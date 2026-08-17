# Validação do instalador Windows

- Repositório: https://github.com/LuquinhasBohrer/e2ps-manual-builder
- Commit da funcionalidade Limpar tudo: `1882e9d` — `feat: add clear all action for new manuals`.
- Commit do workflow de publicação: `a7a2602` — `fix: publish tagged installers as releases`.
- Tag da nova compilação: `v1.0.3`.
- Execução Windows: https://github.com/LuquinhasBohrer/e2ps-manual-builder/actions/runs/32041093414
- Head SHA da execução v1.0.3: `a7a26023b7ee55f870f786db886e821fee5b27af`.
- Estado verificado: `completed`, `success`.
- Artefato instalador: `E2PS-Manual-Builder-Windows-Installer`, 132426194 bytes, não expirado.
- Artefato portátil: `E2PS-Manual-Builder-Windows-Portable`, 159164725 bytes, não expirado.
- API de artefatos: https://api.github.com/repos/LuquinhasBohrer/e2ps-manual-builder/actions/runs/32041093414/artifacts
- ID do artefato instalador: `9291989178`.
- A Release v1.0.3 ainda não apareceu pela API após o build; o workflow foi corrigido para usar `if: github.ref_type == 'tag'` e a tag foi disparada novamente.
- O instalador anterior baixado pelo usuário pode ser antigo; a versão válida deve ser a artefato da execução 32041093414 ou a futura Release v1.0.3.
