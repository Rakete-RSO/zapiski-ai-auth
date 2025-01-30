import json
import logging
import os
import threading
from typing import Optional
import pika
from sqlalchemy.orm import Session
from .database import get_db
from .models import Billing


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BillingListener(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = False
        self._stop_event = threading.Event()
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self.should_stop = False
        self.thread = None

    def stop(self):
        self._stop_event.set()
        if self.connection and not self.connection.is_closed:
            self.connection.close()

    def callback(self, ch, method, properties, body):
        """Process incoming messages"""
        try:
            billing_data = json.loads(body)
            print(billing_data)

            # Create new billing record
            billing = Billing(
                customer_email=billing_data["customer_email"],
                amount=billing_data["amount"],
                currency=billing_data["currency"],
                payment_intent_id=billing_data["payment_intent_id"],
                client_secret=billing_data["client_secret"],
                status=billing_data["status"],
            )

            # Get database session
            db: Session = next(get_db())
            try:
                db.add(billing)
                db.commit()
                print(f"Stored billing record for {billing_data['customer_email']}")
            except Exception as e:
                db.rollback()
                print(f"Error storing billing record: {str(e)}")
            finally:
                db.close()

        except json.JSONDecodeError as e:
            print(f"Error decoding message: {str(e)}")
        except Exception as e:
            print(f"Error processing message: {str(e)}")

    def start_consuming(self):
        """Start consuming messages"""
        try:
            self.channel.basic_consume(
                queue="billing_results",
                on_message_callback=self.callback,
                auto_ack=True,
            )
            print("Started consuming billing messages...")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Unexpected error in billing worker: {e}")
            if not self._stop_event.is_set():
                logger.info("Restarting worker in 5 seconds...")
                self._stop_event.wait(timeout=5.0)

    def stop(self):
        """Stop the listener"""
        if self.channel:
            self.channel.stop_consuming()
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        if self.thread:
            self.thread.join(timeout=1.0)

    def get_rabbitmq_connection(self):
        credentials = pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "user"), os.getenv("RABBITMQ_PASS", "password")
        )
        parameters = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=5672,
            credentials=credentials,
        )
        return pika.BlockingConnection(parameters)

    def run(self):
        while not self._stop_event.is_set():
            try:
                self.connection = self.get_rabbitmq_connection()
                self.channel = self.connection.channel()

                self.channel.basic_qos(prefetch_count=1)
                logger.info("Billing worker started. Waiting for billing requests...")
                self.start_consuming()

            except pika.exceptions.AMQPConnectionError as e:
                logger.error(f"AMQP Connection error: {e}")
                if not self._stop_event.is_set():
                    logger.info("Attempting to reconnect in 5 seconds...")
                    self._stop_event.wait(timeout=5.0)
            except Exception as e:
                logger.error(f"Unexpected error in billing worker: {e}")
                if not self._stop_event.is_set():
                    logger.info("Restarting worker in 5 seconds...")
                    self._stop_event.wait(timeout=5.0)
