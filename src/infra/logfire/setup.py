import logfire
from dependency_injector.providers import ConfigurationOption


def setup_logfire(settings: ConfigurationOption) -> None:
    logfire.configure(
        token=settings.token().get_secret_value() or None,
        environment=settings.environment(),
        service_name=settings.service_name(),
        send_to_logfire=settings.send_to_logfire(),
        console=False,
    )
    logfire.instrument_pydantic_ai()
