import logging

from app.services.collection_service import run_collection


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )


def main() -> None:
    configure_logging()

    try:
        run_collection()
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("Collection stopped by user.")
    except Exception:
        logging.getLogger(__name__).exception("Collection terminated unexpectedly.")
        raise


if __name__ == "__main__":
    main()
