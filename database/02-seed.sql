INSERT INTO postos(nome,cidade,media_atendimento_minutos) VALUES
  ('SAC Shopping da Bahia — DEMONSTRAÇÃO','Salvador',8),
  ('SAC Feira de Santana — DEMONSTRAÇÃO','Feira de Santana',7);
INSERT INTO filas(posto_id) SELECT id FROM postos;
INSERT INTO guiches(posto_id,nome,ativo)
SELECT id,'Guichê 1',TRUE FROM postos;
INSERT INTO guiches(posto_id,nome,ativo)
SELECT id,'Guichê 2',TRUE FROM postos;
