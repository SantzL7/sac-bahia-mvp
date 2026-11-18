CREATE TABLE IF NOT EXISTS postos (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nome TEXT NOT NULL,
  cidade TEXT NOT NULL,
  media_atendimento_minutos INTEGER NOT NULL DEFAULT 8 CHECK(media_atendimento_minutos > 0)
);
CREATE TABLE IF NOT EXISTS filas (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  posto_id INTEGER NOT NULL UNIQUE REFERENCES postos(id),
  proximo_numero INTEGER NOT NULL DEFAULT 1 CHECK(proximo_numero > 0)
);
CREATE TABLE IF NOT EXISTS guiches (
  id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  posto_id INTEGER NOT NULL REFERENCES postos(id),
  nome TEXT NOT NULL,
  ativo BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS senhas (
  id UUID PRIMARY KEY,
  fila_id INTEGER NOT NULL REFERENCES filas(id),
  posto_id INTEGER NOT NULL REFERENCES postos(id),
  numero INTEGER NOT NULL,
  categoria TEXT NOT NULL CHECK(categoria IN ('NORMAL','PRIORITARIA')),
  status TEXT NOT NULL DEFAULT 'AGUARDANDO'
    CHECK(status IN ('AGUARDANDO','CHAMADA','FINALIZADA')),
  guiche_id INTEGER REFERENCES guiches(id),
  idempotency_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  criada_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  chamada_em TIMESTAMPTZ,
  finalizada_em TIMESTAMPTZ,
  UNIQUE(fila_id, numero),
  UNIQUE(fila_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_senhas_aguardando ON senhas (fila_id, categoria, numero) WHERE status='AGUARDANDO';
CREATE TABLE IF NOT EXISTS eventos (
  id UUID PRIMARY KEY,
  posto_id INTEGER NOT NULL REFERENCES postos(id),
  senha_id UUID NOT NULL REFERENCES senhas(id),
  tipo TEXT NOT NULL CHECK(tipo IN ('SENHA_EMITIDA','SENHA_CHAMADA','SENHA_FINALIZADA')),
  payload JSONB NOT NULL,
  correlation_id UUID NOT NULL,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  publicado_em TIMESTAMPTZ,
  tentativas INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_eventos_pendentes ON eventos(criado_em) WHERE publicado_em IS NULL;
CREATE TABLE IF NOT EXISTS eventos_processados (
  evento_id UUID PRIMARY KEY,
  processado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
