"""fundacao

Revision ID: 0001
Revises: 
Criada em: 2026-08-11 11:01:54.579416+00:00
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # citext para e-mail case-insensitive; pg_trgm para similaridade de
    # descrição na conciliação (Fase 4)
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table('contas',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('nome', sa.Text(), nullable=False),
    sa.Column('fuso', sa.Text(), nullable=False),
    sa.Column('moeda', sa.String(length=3), nullable=False),
    sa.Column('idioma', sa.Text(), nullable=False),
    sa.Column('criada_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('usuarios',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('email', postgresql.CITEXT(), nullable=False),
    sa.Column('senha_hash', sa.Text(), nullable=True),
    sa.Column('nome', sa.Text(), nullable=False),
    sa.Column('telefone_e164', sa.Text(), nullable=True),
    sa.Column('telefone_verificado_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('telefone_e164')
    )
    op.create_table('categorias',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('conta_id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.Text(), nullable=False),
    sa.Column('tipo', sa.Enum('entrada', 'saida', name='tipo_fluxo'), nullable=False),
    sa.Column('cor', sa.Text(), nullable=True),
    sa.Column('icone', sa.Text(), nullable=True),
    sa.Column('parent_id', sa.UUID(), nullable=True),
    sa.Column('palavras_chave', sa.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('orcamento_mensal_centavos', sa.BigInteger(), nullable=True),
    sa.Column('meta_receita_centavos', sa.BigInteger(), nullable=True),
    sa.Column('sistema', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['categorias.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('conta_id', 'nome', 'tipo', name='uq_categoria_nome_tipo')
    )
    op.create_index(op.f('ix_categorias_conta_id'), 'categorias', ['conta_id'], unique=False)
    op.create_table('contas_bancarias',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('conta_id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.Text(), nullable=False),
    sa.Column('instituicao', sa.Text(), nullable=True),
    sa.Column('tipo', sa.Text(), nullable=True),
    sa.Column('saldo_centavos', sa.BigInteger(), nullable=False),
    sa.Column('saldo_atualizado_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('conexao_id', sa.UUID(), nullable=True),
    sa.Column('externo_id', sa.Text(), nullable=True),
    sa.Column('incluir_no_total', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contas_bancarias_conta_id'), 'contas_bancarias', ['conta_id'], unique=False)
    op.create_table('membros_conta',
    sa.Column('conta_id', sa.UUID(), nullable=False),
    sa.Column('usuario_id', sa.UUID(), nullable=False),
    sa.Column('papel', sa.Enum('dono', 'administrador', 'membro', 'leitor', name='papel_conta'), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('conta_id', 'usuario_id')
    )
    op.create_table('operacoes',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('conta_id', sa.UUID(), nullable=False),
    sa.Column('usuario_id', sa.UUID(), nullable=True),
    sa.Column('ator', sa.Text(), nullable=False),
    sa.Column('acao', sa.Text(), nullable=False),
    sa.Column('entidade', sa.Text(), nullable=False),
    sa.Column('entidade_id', sa.UUID(), nullable=True),
    sa.Column('antes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('depois', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('idempotency_key', sa.Text(), nullable=True),
    sa.Column('revertida_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revertida_por_op', sa.UUID(), nullable=True),
    sa.Column('mensagem_id', sa.UUID(), nullable=True),
    sa.Column('criada_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['revertida_por_op'], ['operacoes.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_operacoes_conta_data', 'operacoes', ['conta_id', 'criada_em'], unique=False)
    op.create_index(op.f('ix_operacoes_conta_id'), 'operacoes', ['conta_id'], unique=False)
    op.create_index('uq_operacoes_idempotency', 'operacoes', ['conta_id', 'idempotency_key'], unique=True, postgresql_where=sa.text('idempotency_key IS NOT NULL'))
    op.create_table('pessoas',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('conta_id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.Text(), nullable=False),
    sa.Column('apelidos', sa.ARRAY(sa.Text()), server_default='{}', nullable=False),
    sa.Column('telefone_e164', sa.Text(), nullable=True),
    sa.Column('email', postgresql.CITEXT(), nullable=True),
    sa.Column('documento', sa.Text(), nullable=True),
    sa.Column('origem', sa.Text(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pessoas_conta_id'), 'pessoas', ['conta_id'], unique=False)
    op.create_table('cartoes',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('conta_id', sa.UUID(), nullable=False),
    sa.Column('nome', sa.Text(), nullable=False),
    sa.Column('bandeira', sa.Text(), nullable=True),
    sa.Column('limite_centavos', sa.BigInteger(), nullable=True),
    sa.Column('dia_fechamento', sa.SmallInteger(), nullable=False),
    sa.Column('dia_vencimento', sa.SmallInteger(), nullable=False),
    sa.Column('conta_pagamento_id', sa.UUID(), nullable=True),
    sa.Column('conexao_id', sa.UUID(), nullable=True),
    sa.Column('externo_id', sa.Text(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('dia_fechamento BETWEEN 1 AND 31', name='ck_cartao_fechamento'),
    sa.CheckConstraint('dia_vencimento BETWEEN 1 AND 31', name='ck_cartao_vencimento'),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['conta_pagamento_id'], ['contas_bancarias.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cartoes_conta_id'), 'cartoes', ['conta_id'], unique=False)
    op.create_table('faturas',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('conta_id', sa.UUID(), nullable=False),
    sa.Column('cartao_id', sa.UUID(), nullable=False),
    sa.Column('competencia', sa.Date(), nullable=False),
    sa.Column('data_fechamento', sa.Date(), nullable=False),
    sa.Column('data_vencimento', sa.Date(), nullable=False),
    sa.Column('total_centavos', sa.BigInteger(), nullable=False),
    sa.Column('pago_centavos', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.Enum('aberta', 'fechada', 'paga', 'parcial', name='status_fatura'), nullable=False),
    sa.ForeignKeyConstraint(['cartao_id'], ['cartoes.id'], ),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cartao_id', 'competencia', name='uq_fatura_competencia')
    )
    op.create_index(op.f('ix_faturas_conta_id'), 'faturas', ['conta_id'], unique=False)
    op.create_table('series',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('conta_id', sa.UUID(), nullable=False),
    sa.Column('tipo', sa.Enum('recorrente', 'parcelada', name='tipo_serie'), nullable=False),
    sa.Column('descricao', sa.Text(), nullable=False),
    sa.Column('tipo_fluxo', sa.Enum('entrada', 'saida', name='tipo_fluxo'), nullable=False),
    sa.Column('valor_centavos', sa.BigInteger(), nullable=False),
    sa.Column('categoria_id', sa.UUID(), nullable=True),
    sa.Column('conta_bancaria_id', sa.UUID(), nullable=True),
    sa.Column('cartao_id', sa.UUID(), nullable=True),
    sa.Column('pessoa_id', sa.UUID(), nullable=True),
    sa.Column('freq', sa.Enum('diaria', 'semanal', 'quinzenal', 'mensal', 'bimestral', 'trimestral', 'semestral', 'anual', name='frequencia'), nullable=True),
    sa.Column('dia_do_mes', sa.SmallInteger(), nullable=True),
    sa.Column('politica_dia_util', sa.Text(), nullable=False),
    sa.Column('data_inicio', sa.Date(), nullable=False),
    sa.Column('data_fim', sa.Date(), nullable=True),
    sa.Column('total_parcelas', sa.SmallInteger(), nullable=True),
    sa.Column('ativa', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['cartao_id'], ['cartoes.id'], ),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ),
    sa.ForeignKeyConstraint(['conta_bancaria_id'], ['contas_bancarias.id'], ),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['pessoa_id'], ['pessoas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_series_conta_id'), 'series', ['conta_id'], unique=False)
    op.create_table('series_excecoes',
    sa.Column('serie_id', sa.UUID(), nullable=False),
    sa.Column('data_prevista', sa.Date(), nullable=False),
    sa.Column('acao', sa.Text(), nullable=False),
    sa.Column('transacao_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['serie_id'], ['series.id'], ),
    sa.PrimaryKeyConstraint('serie_id', 'data_prevista')
    )
    op.create_table('transacoes',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('conta_id', sa.UUID(), nullable=False),
    sa.Column('criado_por', sa.UUID(), nullable=True),
    sa.Column('tipo', sa.Enum('entrada', 'saida', name='tipo_fluxo'), nullable=False),
    sa.Column('descricao', sa.Text(), nullable=False),
    sa.Column('valor_centavos', sa.BigInteger(), nullable=False),
    sa.Column('data_competencia', sa.Date(), nullable=False),
    sa.Column('data_efetiva', sa.Date(), nullable=True),
    sa.Column('status', sa.Enum('previsto', 'realizado', 'cancelado', name='status_transacao'), nullable=False),
    sa.Column('categoria_id', sa.UUID(), nullable=True),
    sa.Column('categoria_travada', sa.Boolean(), nullable=False),
    sa.Column('conta_bancaria_id', sa.UUID(), nullable=True),
    sa.Column('cartao_id', sa.UUID(), nullable=True),
    sa.Column('fatura_id', sa.UUID(), nullable=True),
    sa.Column('pessoa_id', sa.UUID(), nullable=True),
    sa.Column('serie_id', sa.UUID(), nullable=True),
    sa.Column('parcela_num', sa.SmallInteger(), nullable=True),
    sa.Column('origem', sa.Enum('manual', 'agente', 'open_finance', 'serie', 'importacao', name='origem_registro'), nullable=False),
    sa.Column('externo_id', sa.Text(), nullable=True),
    sa.Column('hash_dedup', sa.Text(), nullable=True),
    sa.Column('observacao', sa.Text(), nullable=True),
    sa.Column('anexos', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('valor_centavos > 0', name='ck_transacao_valor_positivo'),
    sa.ForeignKeyConstraint(['cartao_id'], ['cartoes.id'], ),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], ),
    sa.ForeignKeyConstraint(['conta_bancaria_id'], ['contas_bancarias.id'], ),
    sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], ),
    sa.ForeignKeyConstraint(['criado_por'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['fatura_id'], ['faturas.id'], ),
    sa.ForeignKeyConstraint(['pessoa_id'], ['pessoas.id'], ),
    sa.ForeignKeyConstraint(['serie_id'], ['series.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transacoes_conta_categoria', 'transacoes', ['conta_id', 'categoria_id', 'data_competencia'], unique=False)
    op.create_index('ix_transacoes_conta_competencia', 'transacoes', ['conta_id', 'data_competencia'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index(op.f('ix_transacoes_conta_id'), 'transacoes', ['conta_id'], unique=False)
    op.create_index('ix_transacoes_hash_dedup', 'transacoes', ['conta_id', 'hash_dedup'], unique=False, postgresql_where=sa.text('hash_dedup IS NOT NULL'))
    op.create_index('uq_transacoes_externo', 'transacoes', ['conta_id', 'externo_id'], unique=True, postgresql_where=sa.text('externo_id IS NOT NULL'))


def downgrade() -> None:
    op.drop_index('uq_transacoes_externo', table_name='transacoes', postgresql_where=sa.text('externo_id IS NOT NULL'))
    op.drop_index('ix_transacoes_hash_dedup', table_name='transacoes', postgresql_where=sa.text('hash_dedup IS NOT NULL'))
    op.drop_index(op.f('ix_transacoes_conta_id'), table_name='transacoes')
    op.drop_index('ix_transacoes_conta_competencia', table_name='transacoes', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('ix_transacoes_conta_categoria', table_name='transacoes')
    op.drop_table('transacoes')
    op.drop_table('series_excecoes')
    op.drop_index(op.f('ix_series_conta_id'), table_name='series')
    op.drop_table('series')
    op.drop_index(op.f('ix_faturas_conta_id'), table_name='faturas')
    op.drop_table('faturas')
    op.drop_index(op.f('ix_cartoes_conta_id'), table_name='cartoes')
    op.drop_table('cartoes')
    op.drop_index(op.f('ix_pessoas_conta_id'), table_name='pessoas')
    op.drop_table('pessoas')
    op.drop_index('uq_operacoes_idempotency', table_name='operacoes', postgresql_where=sa.text('idempotency_key IS NOT NULL'))
    op.drop_index(op.f('ix_operacoes_conta_id'), table_name='operacoes')
    op.drop_index('ix_operacoes_conta_data', table_name='operacoes')
    op.drop_table('operacoes')
    op.drop_table('membros_conta')
    op.drop_index(op.f('ix_contas_bancarias_conta_id'), table_name='contas_bancarias')
    op.drop_table('contas_bancarias')
    op.drop_index(op.f('ix_categorias_conta_id'), table_name='categorias')
    op.drop_table('categorias')
    op.drop_table('usuarios')
    op.drop_table('contas')

    # os tipos ENUM não caem junto com as tabelas: o downgrade só é funcional
    # de verdade se derrubar cada um (CLAUDE.md §8)
    for tipo in (
        "origem_registro",
        "status_transacao",
        "frequencia",
        "tipo_serie",
        "status_fatura",
        "tipo_fluxo",
        "papel_conta",
    ):
        op.execute(f"DROP TYPE IF EXISTS {tipo}")

    # as extensões podem estar em uso por outro schema; não são derrubadas.
