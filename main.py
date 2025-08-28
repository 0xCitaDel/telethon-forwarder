import asyncio
import logging
from aiohttp import ClientSession

from src.account_worker import AccountWorker
from src.config import load_accounts_from_config
from src.webhook import WebhookClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

log = logging.getLogger("tg-forwarder")


async def amain():
    accounts = load_accounts_from_config()

    async with ClientSession() as aio:
        http = WebhookClient(aio)
        workers = [AccountWorker(account_config, http) for account_config in accounts]

        for w in workers:
            await w.start()

        tasks = [asyncio.create_task(w.run_forever(), name=f"worker:{w.cfg.name}") for w in workers]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            for w in workers:
                await w.stop()


def main():
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        log.info("Interrupted by user")


if __name__ == "__main__":
    main()
