SELECT * FROM inversion.20260428_bvq1;

valor_nominal,
valor_efectivo,
precio,
precio_neto,
comision_bolsa,
comision_operador,
total_comprador_neto



SELECT `20260428_bvq1`.`tipo_documento`,
    `20260428_bvq1`.`operacion_no`,
    `20260428_bvq1`.`titulo_valor`,
    `20260428_bvq1`.`emisor`,
    `20260428_bvq1`.`valor_nominal`,
    `20260428_bvq1`.`cantidad`,
    `20260428_bvq1`.`valor_efectivo`,
    `20260428_bvq1`.`precio`,
    `20260428_bvq1`.`precio_neto`,
    `20260428_bvq1`.`comision_bolsa`,
    `20260428_bvq1`.`comision_operador`,
    `20260428_bvq1`.`total_comisiones`,
    `20260428_bvq1`.`total_comprador_neto`,
    `20260428_bvq1`.`moneda`,
    `20260428_bvq1`.`mercado`,
    `20260428_bvq1`.`postura`,
    `20260428_bvq1`.`tipo_operacion`,
    `20260428_bvq1`.`fecha_valor`,
    `20260428_bvq1`.`calificacion`,
    `20260428_bvq1`.`codigo_vector`,
    `20260428_bvq1`.`archivo`,
    `20260428_bvq1`.`fecha_procesamiento`,
    `20260428_bvq1`.`ruta_completa`,
    `20260428_bvq1`.`tamaÃ±o_archivo`
FROM `inversion`.`20260428_bvq1`;



UPDATE inversion.20260428_bvq1
SET 
    valor_nominal        = REPLACE(valor_nominal, ',', '.'),
    valor_efectivo       = REPLACE(valor_efectivo, ',', '.'),
    precio               = REPLACE(precio, ',', '.'),
    precio_neto          = REPLACE(precio_neto, ',', '.'),
    comision_bolsa       = REPLACE(comision_bolsa, ',', '.'),
    comision_operador    = REPLACE(comision_operador, ',', '.'),
    total_comprador_neto = REPLACE(total_comprador_neto, ',', '.')
WHERE 
    valor_nominal        LIKE '%,%' OR
    valor_efectivo       LIKE '%,%' OR
    precio               LIKE '%,%' OR
    precio_neto          LIKE '%,%' OR
    comision_bolsa       LIKE '%,%' OR
    comision_operador    LIKE '%,%' OR
    total_comprador_neto LIKE '%,%';



