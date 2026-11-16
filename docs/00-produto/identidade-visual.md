# Identidade visual: Cursos Corporativos

Primeira aplicação: tela de login. A direção visual conecta a organização de demandas à criação de cursos, com IA como apoio e revisão humana como parte do processo. O nome do produto foi preservado.

## Paleta

Os tokens estão em `web/src/styles/tokens.css`. As demais telas ainda usam a paleta anterior; a migração será feita por tela.

| Token | Cor | Uso |
| --- | --- | --- |
| `--brand-forest-deep` | `#102E29` | Painéis institucionais |
| `--brand-forest` | `#173E36` | Ação principal e elementos de marca |
| `--brand-forest-hover` | `#245548` | Hover da ação principal |
| `--brand-lime` | `#D9EE9A` | Ênfase sobre fundo escuro; sem texto branco |
| `--brand-ivory` | `#F7F8F2` | Fundo da área de trabalho |
| `--brand-paper` | `#FFFFFF` | Campos e superfícies |
| `--brand-ink` | `#203A33` | Texto principal |
| `--brand-muted` | `#64756E` | Texto secundário |
| `--brand-line` | `#DCE3DA` | Bordas e divisores |
| `--brand-danger` | `#A52B35` | Erros acompanhados de mensagem textual |
| `--brand-focus` | `#426D51` | Contorno de foco pelo teclado |

## Linguagem visual

- Marca geométrica em camadas: representa informação ganhando estrutura.
- Tipografia de sistema (`Segoe UI` no Windows), sem download de fontes. Títulos com espaçamento mais fechado; formulários com rótulos explícitos.
- Verde profundo transmite organização e confiança. Marfim traz leveza à operação diária; lima destaca inteligência e evolução.
- Campos e botões com raio de 12 px; contêineres com cantos suaves e sombras discretas.
- Ícones lineares, bordas finas e espaços generosos. Evitar gradientes decorativos e excesso de cartões.
- Tom de voz direto, humano e ligado à tarefa. Não prometer envio automático, recuperação de senha ou integrações sem implementação.

## Login

No desktop, o painel institucional apresenta uma transformação ilustrativa de demanda em curso. Ele não exibe dados reais nem resultados de uma execução de IA. O formulário permanece como área independente e prioritária.

No celular, a apresentação é reduzida e o exemplo ilustrativo é ocultado para manter o acesso próximo do topo. A tela preserva os estados de validação, carregamento, feedback de erro e redirecionamento da autenticação existente. O controle de visibilidade da senha possui nome acessível e não envia o formulário.

As cores de estado devem sempre acompanhar texto ou ícone. Controles precisam de foco visível, navegação pelo teclado e respeito à preferência por movimento reduzido.
