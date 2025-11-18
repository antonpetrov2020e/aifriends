#!/usr/bin/env python3
"""
Standalone webhook server for YooKassa payment notifications
Run this separately from the main bot to handle payment webhooks

Usage:
    python run_webhook.py [--port PORT]

Default port: 8080
"""
import asyncio
import logging
import sys
import argparse

from src.config import settings
from src.database import init_db, get_session
from src.webhook import YooKassaWebhookServer
from src.services.payment_service import PaymentService


# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.log_level),
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for webhook server"""
    parser = argparse.ArgumentParser(description="YooKassa webhook server")
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to listen on (default: 8080)"
    )
    args = parser.parse_args()

    # Check if YooKassa credentials are configured
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        logger.error("YooKassa credentials not configured!")
        logger.error("Set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY in .env file")
        sys.exit(1)

    # Initialize database
    logger.info("Initializing database...")
    engine = init_db(settings.database_url)
    db_session = get_session(engine)

    # Initialize payment service
    logger.info("Initializing Payment service...")
    payment_service = PaymentService(
        db_session=db_session,
        shop_id=settings.yookassa_shop_id,
        secret_key=settings.yookassa_secret_key,
    )

    # Create and run webhook server
    logger.info(f"Starting YooKassa webhook server on port {args.port}...")
    logger.info("Webhook URL: http://YOUR_DOMAIN:{}/webhook/yookassa".format(args.port))
    logger.info("Configure this URL in YooKassa dashboard")

    server = YooKassaWebhookServer(payment_service, port=args.port)
    server.run()  # Blocking call


if __name__ == "__main__":
    main()
