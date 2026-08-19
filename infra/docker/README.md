# Recursos de container

Cada microsserviço tem seu próprio `Dockerfile`, junto do código. Esta pasta guarda o que é
compartilhado entre eles.

Previsto:

- imagem base comum dos serviços Python, se a duplicação entre os quatro `Dockerfile` justificar;
- `Dockerfile` do frontend para build de produção (servido como estático);
- override de Compose para homologação.

A orquestração local fica no [`docker-compose.yml`](../../docker-compose.yml) da raiz.
