"""
YooKassa webhook server for payment notifications
Runs alongside the Telegram bot to process payment updates
"""
import asyncio
import logging
from aiohttp import web
from sqlalchemy.orm import Session

from .database import get_session
from .services.payment_service import PaymentService
from .config import settings

logger = logging.getLogger(__name__)


class YooKassaWebhookServer:
    """
    HTTP server for receiving YooKassa payment webhooks
    """

    def __init__(self, payment_service: PaymentService, port: int = 8080):
        """
        Initialize webhook server

        Args:
            payment_service: Payment service instance
            port: Port to listen on (default: 8080)
        """
        self.payment_service = payment_service
        self.port = port
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        """Set up HTTP routes"""
        self.app.router.add_post('/webhook/yookassa', self.handle_webhook)
        self.app.router.add_get('/health', self.health_check)

    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({"status": "ok"})

    async def handle_webhook(self, request):
        """
        Handle incoming YooKassa webhook

        YooKassa sends POST requests with payment status updates
        """
        try:
            # Parse webhook data
            webhook_data = await request.json()

            logger.info(f"Received YooKassa webhook: {webhook_data.get('event')}")

            # Process webhook using payment service
            success = await self.payment_service.process_webhook(webhook_data)

            if success:
                logger.info("Webhook processed successfully")
                return web.json_response({"status": "ok"}, status=200)
            else:
                logger.warning("Webhook processing failed")
                return web.json_response({"status": "error"}, status=400)

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def start(self):
        """Start the webhook server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"YooKassa webhook server started on port {self.port}")

    def run(self):
        """Run webhook server (blocking)"""
        logger.info(f"Starting YooKassa webhook server on port {self.port}")
        web.run_app(self.app, host='0.0.0.0', port=self.port)


async def start_webhook_server(payment_service: PaymentService, port: int = 8080):
    """
    Start webhook server as async task

    Args:
        payment_service: Payment service instance
        port: Port to listen on

    Returns:
        Coroutine that runs the server
    """
    server = YooKassaWebhookServer(payment_service, port)
    await server.start()
    # Keep running indefinitely
    await asyncio.Event().wait()
