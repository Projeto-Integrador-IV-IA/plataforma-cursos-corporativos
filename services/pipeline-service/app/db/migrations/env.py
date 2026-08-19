"""Ambiente de execucao das migrations do Alembic.

Contrato desta camada:
    - ler a URL do banco de ``DATABASE_URL`` (nunca do alembic.ini) - RNF11;
    - expor o metadata de ``app.db.base`` para autogeracao;
    - suportar modo offline (gera SQL) e online (aplica no banco).

Migrations sao parte da trilha de auditoria da modelagem: nenhuma alteracao de
schema entra sem migration versionada (RNF08, RNF09, RNF14).

TODO(scaffolding): implementar ``run_migrations_offline()`` e ``run_migrations_online()``.
"""
