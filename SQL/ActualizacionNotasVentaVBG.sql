SELECT * FROM inversion.20260429_bvg1;

UPDATE 20260429_bvg1
SET precio = SUBSTRING_INDEX(precio, '.', 2);


UPDATE 20260429_bvg1
SET comision_bolsa = REPLACE(
                    comision_bolsa,
                    CONCAT('.', SUBSTRING_INDEX(comision_bolsa, '.', -1)),
                    SUBSTRING_INDEX(comision_bolsa, '.', -1)
                );
                
                
UPDATE 20260429_bvg1
SET precio_neto =
    CONCAT(
        LEFT(REPLACE(precio_neto, '.', ''), 2),
        '.',
        SUBSTRING(REPLACE(precio_neto, '.', ''), 3)
    );
    
    
    
    INSERT INTO `inversion`.`inversion`
(-- `id`,
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
  91, -- <{inv_tipo: }>,
  '2026-04-28', -- <{inv_fecha_compra: }>,
  'Jhon', -- <{inv_propietario: }>,
  operacion_no, -- <{inv_liquidacion: }>,
  222, -- <{inv_instrumento: }>,
  null, -- <{inv_fecha_emision: }>,
  null, -- <{inv_fecha_vencimiento: }>,
  null, -- <{inv_fecha_venta: }>,
  'SRI 2034-12-31', -- <{inv_emisor: }>,
  null, -- <{inv_calificacion_riesgo: }>,
  valor_nominal, -- <{inv_valor_nominal: }>,
  monto_a_negociar, -- <{inv_monto_a_negociar: }>,
  total_comprador_neto, -- <{inv_capital_invertido: }>,
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
  total_comisiones, -- <{inv_total_comisiones: }>,
null, -- <{inv_codigo_SEB: }>,
null, -- <{inv_codigo_BCE: }>,
null, -- <{inv_fechas_pagos_capital: }>,
'SRI 2034-12-31', -- <{id_instrumento: }>,
1, -- <{is_active: 1}>,
0, -- <{is_deleted: 0}>,
current_timestamp(), -- <{created_at: current_timestamp()}>,
current_timestamp() -- <{updated_at: current_timestamp()}>)

from 20260429_bvg1
;

select * from inversion    
select * from instrumento
SELECT * FROM sipro.emisor

update inversion set inv_instrumento = 'SRI 2034-12-31' where inv_instrumento = 222
update inversion set id_instrumento = 222  where id_instrumento = 'SRI 2034-12-31'


select 5728.65 + 471.35
select * from amortizacion order by id desc
select count(*) from amortizacion where am_fecha_pago = '0000-00-00'

update amortizacion set am_fecha_pago = '2034-12-31' where am_fecha_pago = '0000-00-00'    