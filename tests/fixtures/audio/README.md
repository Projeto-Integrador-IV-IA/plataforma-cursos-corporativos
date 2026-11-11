# Audio sintetico para testes RF30

Os arquivos `tone.wav`, `tone.mp3`, `tone.m4a`, `tone.ogg` e `tone.flac`
contem um tom de 440 Hz, mono, 16 kHz, com 1 segundo. Nao contem voz nem dados
de clientes. Foram gerados com FFmpeg a partir do filtro `lavfi`:

```sh
ffmpeg -f lavfi -i sine=frequency=440:sample_rate=16000:duration=1 -ac 1 tone.wav
```

Repetir com cada extensao. O encoder pode introduzir padding, portanto a
duracao medida em formatos comprimidos pode ultrapassar ligeiramente 1 segundo.
FFmpeg nao e uma dependencia de execucao ou dos testes: as fixtures prontas
sao versionadas; o servico usa Mutagen para ler o formato e a duracao.
