from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from langgraph.checkpoint.postgres import _ainternal
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.base import SerializerProtocol
from psycopg import AsyncConnection
from psycopg.rows import dict_row

Conn = _ainternal.Conn  # For backward compatibility


class SemiCustomAsyncPostgresSaver(AsyncPostgresSaver):
    """A custom postgres saver class for only an additional method."""

    @classmethod
    @asynccontextmanager
    async def from_conn_string(
        cls,
        conn_string: str,
        *,
        pipeline: bool = False,
        serde: Optional[SerializerProtocol] = None,
    ) -> AsyncIterator["SemiCustomAsyncPostgresSaver"]:
        """Create a new SemiCustomAsyncPostgresSaver instance from a connection string.
        Args:
            conn_string (str): The Postgres connection info string.
            pipeline (bool): whether to use AsyncPipeline
        Returns:
            SemiCustomAsyncPostgresSaver: A new SemiCustomAsyncPostgresSaver instance.
        """
        async with await AsyncConnection.connect(
            conn_string, autocommit=True, prepare_threshold=0, row_factory=dict_row
        ) as conn:
            if pipeline:
                async with conn.pipeline() as pipe:
                    yield cls(conn=conn, pipe=pipe, serde=serde)
            else:
                yield cls(conn=conn, serde=serde)

    async def get_user_threads(
        self, query: str, user_id: str, limit: int = 10, offset: int = 0
    ):
        """Retrieve all user's thread ids, sorted in the latest order.
        Args:
            query (str): query to execute.
            user_id (str): User ID.
            limit (int, optional): Page size. Defaults to 10.
            offset (int, optional): Page number offset. Defaults to 0.
        """

        # feth user threads
        async with self._cursor(pipeline=True) as cur:
            await cur.execute(
                query,
                (user_id, limit, offset),
            )

            # iterate over list
            async for val in cur:
                yield (
                    val["thread_id"],
                    val["user_id"],
                    val["message"],
                    val["created_at"],
                )
