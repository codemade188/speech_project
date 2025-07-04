"""Allow audio_url to be nullable

Revision ID: 1803e8c01f08
Revises: 3e9420da3289
Create Date: 2025-05-01 19:32:54.634044

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '1803e8c01f08'
down_revision = '3e9420da3289'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.alter_column('audio_url',
               existing_type=mysql.VARCHAR(length=2048),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.alter_column('audio_url',
               existing_type=mysql.VARCHAR(length=2048),
               nullable=False)

    # ### end Alembic commands ###
