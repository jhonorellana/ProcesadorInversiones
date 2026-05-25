SELECT * FROM inversion.20260428_bvq1;

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
    
    


INSERT INTO `inversion`.`inversion`
( -- `id`,
`inv_tipo`,
`inv_fecha_compra`,
`inv_propietario`,
`inv_liquidacion`,
`inv_instrumento`,
`inv_fecha_emision`,
`inv_fecha_vencimiento`,
`inv_fecha_venta`,
`inv_emisor`,
`inv_calificacion_riesgo`,
`inv_valor_nominal`,
`inv_monto_a_negociar`,
`inv_capital_invertido`,
`inv_tasa_interes`,
`inv_rendimiento_nominal`,
`inv_rendimiento_efectivo`,
`inv_valor_efectivo`,
`inv_valor_interes`,
`inv_comision_bolsa`,
`inv_comision_operador`,
`inv_retencion`,
`inv_expirado`,
`inv_pagada`,
`inv_tasa_mensual_real`,
`inv_interes_primer_mes`,
`inv_fecha_primer_pago`,
`inv_precio_comprado`,
`inv_precio_neto_comprado`,
`inv_valor_sin_comision`,
`inv_valor_con_interes`,
`inv_interes_acumulado_previo`,
`inv_total_comisiones`,
`inv_codigo_SEB`,
`inv_codigo_BCE`,
`inv_fechas_pagos_capital`,
`id_instrumento`,
`is_active`,
`is_deleted`,
`created_at`,
`updated_at`)

select 
 -- <{id: }>,
titulo_valor, -- <{inv_tipo: }>,
'2026-04-28', -- <{inv_fecha_compra: }>,
'Jhon', -- <{inv_propietario: }>,
operacion_no, -- <{inv_liquidacion: }>,
'SRI 2034-12-31', -- <{inv_instrumento: }>,
null, -- <{inv_fecha_emision: }>,
null, -- <{inv_fecha_vencimiento: }>,
null, -- <{inv_fecha_venta: }>,
'SRI 2034-12-31', -- <{inv_emisor: }>,
null, -- <{inv_calificacion_riesgo: }>,
valor_nominal, -- <{inv_valor_nominal: }>,
valor_nominal, -- <{inv_monto_a_negociar: }>,
3770.5566, -- <{inv_capital_invertido: }>,
1, -- <{inv_tasa_interes: }>,
1, -- <{inv_rendimiento_nominal: }>,
1, -- <{inv_rendimiento_efectivo: }>,
valor_efectivo, -- <{inv_valor_efectivo: }>,
0, -- <{inv_valor_interes: }>,
comision_bolsa, -- <{inv_comision_bolsa: }>,
comision_operador, -- <{inv_comision_operador: }>,
0, -- <{inv_retencion: }>,
0, -- <{inv_expirado: 0}>,
0, -- <{inv_pagada: 0}>,
1, -- <{inv_tasa_mensual_real: }>,
0, -- <{inv_interes_primer_mes: }>,
null, -- <{inv_fecha_primer_pago: }>,
precio, -- <{inv_precio_comprado: }>,
precio_neto, -- <{inv_precio_neto_comprado: }>,
valor_efectivo, -- <{inv_valor_sin_comision: }>,
total_comprador_neto, -- <{inv_valor_con_interes: }>,
0, -- <{inv_interes_acumulado_previo: }>,
comision_operador + comision_bolsa, -- <{inv_total_comisiones: }>,
null, -- <{inv_codigo_SEB: }>,
null, -- <{inv_codigo_BCE: }>,
null, -- <{inv_fechas_pagos_capital: }>,
'SRI 2034-12-31', -- <{id_instrumento: }>,
1, -- <{is_active: 1}>,
0, -- <{is_deleted: 0}>,
current_timestamp(), -- <{created_at: current_timestamp()}>,
current_timestamp() -- <{updated_at: current_timestamp()}>);
from 
inversion.20260428_bvq1;


select * from inversion where inv_tipo = 73;

select * from amortizacion order by id desc -- 387

UPDATE amortizacion A
JOIN inversion I ON I.id = A.inv_id
SET A.am_fecha_pago = '2034-12-31',
    A.am_capital = I.inv_capital_invertido,
    A.am_total = I.inv_capital_invertido
WHERE A.inv_id IN (388, 389, 390, 391);

