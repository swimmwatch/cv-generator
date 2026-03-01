from fastapi_healthchecks.api.router import HealthcheckRouter
from fastapi_healthchecks.api.router import Probe
from fastapi_healthchecks.checks.postgres import PostgreSqlCheck
from fastapi_healthchecks.checks.redis import RedisCheck

from infra.di.container import Container


def make_health_router(container: Container):
    config = container.config

    postgres_sql_check = PostgreSqlCheck(
        host=config.db.host(),
        port=config.db.port(),
        database=config.db.name(),
        username=config.db.user(),
        password=config.db.password(),
    )
    redis_check = RedisCheck(
        host=config.redis.host(),
        port=config.redis.port(),
    )

    return HealthcheckRouter(
        Probe(
            name="readiness",
            checks=[
                postgres_sql_check,
                redis_check,
            ],
        ),
        Probe(
            name="liveness",
            checks=[
                postgres_sql_check,
                redis_check,
            ],
        ),
    )
