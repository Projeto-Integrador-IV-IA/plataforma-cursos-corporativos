# Infraestrutura

Tudo que sustenta o ambiente, sem fazer parte do produto.

```
docker/    Recursos de container compartilhados entre os serviços
db/init/   Scripts executados na primeira criação do banco
scripts/   Utilitários de desenvolvimento
```

## Ambientes

| Ambiente | Onde | Observação |
|---|---|---|
| Local | Docker Compose | Único ambiente do MVP até a Fase 3. |
| Homologação | Camada gratuita/estudantil | Definir na Fase 3 — restrição de RNF12: custo próximo de zero, com a API de linguagem como única despesa recorrente. |

## Restrições

- **RNF12** — operação em camada gratuita/estudantil. Nenhum recurso pago entra sem aprovação da gerência.
- **RNF15** — portabilidade: a aplicação precisa subir como serviço web em ambiente padrão, sem
  depender de recurso proprietário de um provedor específico.
- **RNF11** — segredos apenas por variável de ambiente. Nenhum arquivo desta pasta contém credencial.
