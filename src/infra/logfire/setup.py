import logfire
from dependency_injector.providers import ConfigurationOption


def setup_logfire(settings: ConfigurationOption) -> None:
    send_to_logfire = settings.send_to_logfire()
    token = settings.token().get_secret_value() if send_to_logfire else None

    logfire.configure(
        token=token or None,
        environment=settings.environment(),
        service_name=settings.service_name(),
        send_to_logfire=send_to_logfire,
        console=False,
    )
    logfire.instrument_pydantic_ai()
