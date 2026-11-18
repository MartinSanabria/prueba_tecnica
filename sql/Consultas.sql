-- 1. Obtener conteos por tipo de entidades o individuos por país
SELECT 
    COALESCE(pais, 'NO ESPECIFICADO') AS pais,
    tipo_sujeto,
    fuente,
    COUNT(*) AS total_registros
FROM sujetos_control
GROUP BY COALESCE(pais, 'NO ESPECIFICADO'), tipo_sujeto, fuente
ORDER BY pais ASC, tipo_sujeto ASC, total_registros DESC;


-- 2. Identificar las entidades o individuos con más alias (a.k.a., f.k.a., n.k.a.)
SELECT 
    s.id_sujeto,
    s.fuente,
    s.tipo_sujeto,
    s.nombre_completo,
    COUNT(a.id_alias) AS total_alias,
    COUNT(a.id_alias) FILTER (WHERE LOWER(a.tipo_alias) = 'a.k.a.') AS total_aka,
    COUNT(a.id_alias) FILTER (WHERE LOWER(a.tipo_alias) = 'f.k.a.') AS total_fka,
    COUNT(a.id_alias) FILTER (WHERE LOWER(a.tipo_alias) = 'n.k.a.') AS total_nka,
    COUNT(a.id_alias) FILTER (WHERE LOWER(a.tipo_alias) NOT IN ('a.k.a.', 'f.k.a.', 'n.k.a.')) AS otros_alias_onu
FROM sujetos_control s
INNER JOIN sujetos_alias a ON s.id_sujeto = a.id_sujeto
GROUP BY s.id_sujeto, s.fuente, s.tipo_sujeto, s.nombre_completo
ORDER BY total_alias DESC
LIMIT 20;


-- 3. Identificar las entidades o individuos sin alias (a.k.a., f.k.a., n.k.a.)
SELECT 
    s.id_sujeto,
    s.id_origen,
    s.fuente,
    s.tipo_sujeto,
    s.nombre_completo,
    COALESCE(s.pais, 'NO ESPECIFICADO') AS pais,
    s.programa_sancion
FROM sujetos_control s
LEFT JOIN sujetos_alias a ON s.id_sujeto = a.id_sujeto
WHERE a.id_alias IS NULL
ORDER BY s.fuente, s.tipo_sujeto, s.nombre_completo;


-- 4. Top de países con más registros
SELECT 
    COALESCE(pais, 'NO ESPECIFICADO') AS pais,
    COUNT(*) AS total_registros,
    COUNT(*) FILTER (WHERE tipo_sujeto = 'INDIVIDUO') AS total_individuos,
    COUNT(*) FILTER (WHERE tipo_sujeto = 'ENTIDAD') AS total_entidades,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS porcentaje_total
FROM sujetos_control
GROUP BY COALESCE(pais, 'NO ESPECIFICADO')
ORDER BY total_registros DESC
LIMIT 15;


-- 5A. Nombres completos duplicados entre registros (ej. mismo sujeto en ONU y OFAC o duplicados internos)
SELECT 
    UPPER(TRIM(nombre_completo)) AS nombre_normalizado,
    tipo_sujeto,
    COUNT(*) AS veces_repetido,
    STRING_AGG(id_sujeto || ' (' || fuente || ')', ', ') AS registros_asociados
FROM sujetos_control
GROUP BY UPPER(TRIM(nombre_completo)), tipo_sujeto
HAVING COUNT(*) > 1
ORDER BY veces_repetido DESC, nombre_normalizado ASC;


-- 5B. Combinaciones de primer nombre y apellido duplicados (Individuos)
SELECT 
    UPPER(TRIM(primer_nombre)) AS primer_nombre,
    UPPER(TRIM(apellido)) AS apellido,
    COUNT(*) AS veces_repetido,
    STRING_AGG(id_sujeto, ', ') AS ids_sujetos
FROM sujetos_control
WHERE primer_nombre IS NOT NULL 
  AND apellido IS NOT NULL
GROUP BY UPPER(TRIM(primer_nombre)), UPPER(TRIM(apellido))
HAVING COUNT(*) > 1
ORDER BY veces_repetido DESC;


-- 5C. Alias duplicados entre distintos sujetos o fuentes
SELECT 
    UPPER(TRIM(a.nombre_alias)) AS alias_normalizado,
    COUNT(*) AS veces_repetido,
    COUNT(DISTINCT a.id_sujeto) AS sujetos_distintos,
    STRING_AGG(DISTINCT a.id_sujeto, ', ') AS ids_sujetos
FROM sujetos_alias a
GROUP BY UPPER(TRIM(a.nombre_alias))
HAVING COUNT(*) > 1
ORDER BY veces_repetido DESC, alias_normalizado ASC;