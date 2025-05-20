"""initial_schema

Revision ID: 7960c45348f1
Revises: 4f3e8ad80d29
Create Date: 2025-05-20 10:05:20.665031

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7960c45348f1'
down_revision: Union[str, None] = '4f3e8ad80d29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
