#!/usr/bin/env python3
"""Generate realistic demo data.json for gym-dashboard portfolio."""
import json, random
from datetime import datetime, date, timedelta

random.seed(42)

MONTHS = [f'{y}-{m:02d}' for y in range(2024,2027) for m in range(1,13)
          if f'{y}-{m:02d}' >= '2024-06' and f'{y}-{m:02d}' <= '2026-02']

PROFS = ['Carlos', 'Ana', 'Marcos', 'Julia', 'Pedro', 'Fernanda', 'Rafael']
CONSULTORES = ['Rodrigo', 'Camila', 'Lucas', 'Bruna', 'Felipe']
FONTES = ['Instagram', 'Indicação', 'Google', 'Facebook', 'TikTok', 'Walk-in', 'WhatsApp']
CLASSES = ['Funcional', 'HIIT', 'Pilates', 'Yoga', 'Spinning', 'Boxe', 'CrossTraining']
ARENAS = ['Arena Principal', 'Arena 2', 'Sala Flex']
MOTIVOS = ['Financeiro', 'Mudança de cidade', 'Falta de tempo', 'Insatisfação', 'Viagem', 'Saúde', 'Trabalho']
TIPOS_CANCEL = ['CANCELAMENTO', 'NÃO RENOVAÇÃO']
CATEGORIAS = ['NOVO', 'RENOVACAO', 'RECORRENCIA', 'MIGRACAO', 'PRODUTO', 'AULA']
HORARIOS = ['06:00','07:15','08:15','09:15','10:15','12:15','17:15','18:15','19:15','20:15','21:15']
CONTAS_DESP = ['Aluguel', 'Salários', 'Marketing Digital', 'Manutenção', 'Energia Elétrica',
               'Água e Saneamento', 'Internet / Telefonia', 'Limpeza e Higiene',
               'Material de Escritório', 'Equipamentos', 'Contabilidade', 'Software de Gestão']

def ramp(m, base, growth=0.015, noise=0.12):
    idx = MONTHS.index(m)
    v = base * ((1 + growth) ** idx)
    return int(v * random.uniform(1 - noise, 1 + noise))

# ── leads_monthly ──────────────────────────────────────────
leads_monthly = {}
for m in MONTHS:
    leads_on  = ramp(m, 120, 0.02, 0.15)
    leads_off = ramp(m, 55,  0.01, 0.20)
    leads     = leads_on + leads_off

    marc_on   = int(leads_on  * random.uniform(0.58, 0.70))
    marc_off  = int(leads_off * random.uniform(0.65, 0.80))

    feitas_on  = int(marc_on  * random.uniform(0.80, 0.92))
    feitas_off = int(marc_off * random.uniform(0.78, 0.90))

    planos_on  = int(feitas_on  * random.uniform(0.35, 0.52))
    planos_off = int(feitas_off * random.uniform(0.40, 0.58))

    ticket = random.uniform(195, 245)
    valor_on  = round(planos_on  * ticket * random.uniform(0.92, 1.08), 2)
    valor_off = round(planos_off * ticket * random.uniform(0.92, 1.08), 2)

    leads_monthly[m] = dict(
        leads=leads, exp_marcadas=marc_on+marc_off, exp_feitas=feitas_on+feitas_off,
        planos=planos_on+planos_off, valor=round(valor_on+valor_off, 2),
        leads_online=leads_on, exp_marcadas_online=marc_on, exp_feitas_online=feitas_on,
        planos_online=planos_on, valor_online=valor_on,
        leads_offline=leads_off, exp_marcadas_offline=marc_off, exp_feitas_offline=feitas_off,
        planos_offline=planos_off, valor_offline=valor_off,
    )

# ── exp_monthly & exp_prof ────────────────────────────────
exp_monthly = {}
exp_prof = {p: dict(total=0, fechou=0, valor=0) for p in PROFS}

for m in MONTHS:
    lm = leads_monthly[m]
    total = lm['exp_feitas']
    fechou = lm['planos']
    ticket = lm['valor'] / max(fechou, 1)

    por_fonte = {f: 0 for f in FONTES}
    por_prof  = {p: 0 for p in PROFS}
    por_aula  = {c: 0 for c in CLASSES}

    for _ in range(total):
        f = random.choice(FONTES)
        p = random.choice(PROFS)
        a = random.choice(CLASSES)
        por_fonte[f] += 1
        por_prof[p]  += 1
        por_aula[a]  += 1

    for p, cnt in por_prof.items():
        conv = min(cnt, int(cnt * random.uniform(0.30, 0.55)))
        exp_prof[p]['total']  += cnt
        exp_prof[p]['fechou'] += conv
        exp_prof[p]['valor']  += round(conv * ticket, 2)

    exp_monthly[m] = dict(
        total=total, fechou=fechou, nao_fechou=total-fechou,
        valor=round(lm['valor'], 2),
        por_fonte={k:v for k,v in por_fonte.items() if v},
        por_prof={k:v for k,v in por_prof.items() if v},
        por_aula={k:v for k,v in por_aula.items() if v},
    )

# ── vendas_monthly & vendas_fonte & vendas_consultor_planos
vm_map, vf_map, vendas_consultor = {}, {}, {c: dict(count=0, valor=0) for c in CONSULTORES}

for m in MONTHS:
    for cat in CATEGORIAS:
        if cat == 'NOVO':
            count = ramp(m, 28, 0.02, 0.18)
            ticket = random.uniform(200, 250)
        elif cat == 'RENOVACAO':
            count = ramp(m, 35, 0.015, 0.15)
            ticket = random.uniform(185, 225)
        elif cat == 'RECORRENCIA':
            count = ramp(m, 20, 0.01, 0.20)
            ticket = random.uniform(170, 210)
        elif cat == 'MIGRACAO':
            count = ramp(m, 5, 0.01, 0.25)
            ticket = random.uniform(195, 235)
        elif cat == 'PRODUTO':
            count = ramp(m, 12, 0.01, 0.30)
            ticket = random.uniform(30, 80)
        else:  # AULA
            count = ramp(m, 8, 0.01, 0.25)
            ticket = random.uniform(45, 70)

        valor = round(count * ticket, 2)
        vm_map[f'{m}|{cat}'] = dict(mes=m, categoria=cat, count=count, valor=valor)

        if cat not in ('PRODUTO', 'AULA'):
            c = random.choice(CONSULTORES)
            vendas_consultor[c]['count'] += count
            vendas_consultor[c]['valor'] += valor

    for f in FONTES:
        fcount = ramp(m, 15, 0.015, 0.30)
        fval   = round(fcount * random.uniform(190, 240), 2)
        key = f'{m}|{f}'
        vf_map[key] = dict(mes=m, fonte=f, count=fcount, valor=fval)

# ── cancel_monthly & cancelamentos_raw ──────────────────
cancel_monthly, cancelamentos_raw = {}, []
NOMES = ['João S.','Maria O.','Pedro A.','Ana L.','Carlos M.','Luciana F.',
         'Rafael T.','Beatriz N.','Thiago C.','Isabela R.','Bruno P.','Camila E.']

for m in MONTHS:
    total_c = ramp(m, 14, -0.005, 0.30)
    total_c = max(total_c, 3)
    por_tipo, por_motivo = {}, {}
    val_total = 0
    y, mo = int(m[:4]), int(m[5:7])
    for _ in range(total_c):
        d = date(y, mo, random.randint(1, 28))
        tipo   = random.choices(TIPOS_CANCEL, weights=[4, 6])[0]
        motivo = random.choice(MOTIVOS)
        nome   = random.choice(NOMES)
        val    = round(random.uniform(0, 280), 2) if tipo == 'CANCELAMENTO' else 0
        val_total += val
        por_tipo[tipo]     = por_tipo.get(tipo, 0) + 1
        por_motivo[motivo] = por_motivo.get(motivo, 0) + 1
        cancelamentos_raw.append(dict(data=str(d), nome=nome, valor=val, tipo=tipo, motivo=motivo))

    cancel_monthly[m] = dict(total=total_c, valor=round(val_total, 2),
                             por_tipo=por_tipo, por_motivo=por_motivo)

# ── fin_monthly & financeiro_raw ──────────────────────────
fin_monthly, financeiro_raw = {}, []
for m in MONTHS:
    rec = 0
    desp = 0
    por_conta = {}

    # Receitas (entrada de caixa)
    total_sales = sum(vm_map[k]['valor'] for k in vm_map if k.startswith(m+'|'))
    rec = round(total_sales * random.uniform(0.90, 1.05), 2)
    por_conta['Mensalidades e Planos'] = rec
    financeiro_raw.append(dict(data=f'{m}-05', descricao='Receita de planos e mensalidades',
                               plano_contas='Mensalidades e Planos', valor=rec, status='PAGO'))

    # Despesas
    y, mo = int(m[:4]), int(m[5:7])
    for conta in CONTAS_DESP:
        if conta == 'Aluguel':
            v = -round(random.uniform(14000, 16000), 2)
        elif conta == 'Salários':
            v = -round(random.uniform(22000, 28000), 2)
        elif conta == 'Marketing Digital':
            v = -round(random.uniform(3000, 6000), 2)
        else:
            v = -round(random.uniform(500, 3500), 2)
        desp += abs(v)
        por_conta[conta] = por_conta.get(conta, 0) + v
        d = date(y, mo, random.randint(1, 28))
        financeiro_raw.append(dict(data=str(d), descricao=conta, plano_contas=conta,
                                   valor=v, status=random.choice(['PAGO', 'PAGO', 'PENDENTE'])))

    fin_monthly[m] = dict(receitas=rec, despesas=round(desp, 2), por_conta=por_conta)

# ── aulas_monthly ────────────────────────────────────────
aulas_monthly = {}
for m in MONTHS:
    total_a = ramp(m, 340, 0.008, 0.12)
    ocup_total = 0
    por_prof = {p: dict(aulas=0, ocupacao=0) for p in PROFS}
    por_modal = {c: dict(aulas=0, ocupacao=0) for c in CLASSES}
    por_arena = {a: 0 for a in ARENAS}

    for _ in range(total_a):
        p = random.choice(PROFS)
        c = random.choice(CLASSES)
        a = random.choice(ARENAS)
        ocup = int(random.gauss(15, 4))
        ocup = max(2, min(25, ocup))
        ocup_total += ocup
        por_prof[p]['aulas']    += 1
        por_prof[p]['ocupacao'] += ocup
        por_modal[c]['aulas']    += 1
        por_modal[c]['ocupacao'] += ocup
        por_arena[a]             += 1

    aulas_monthly[m] = dict(
        total=total_a, ocupacao_total=ocup_total,
        por_prof={k:v for k,v in por_prof.items() if v['aulas']},
        por_modalidade={k:v for k,v in por_modal.items() if v['aulas']},
        por_arena={k:v for k,v in por_arena.items() if v},
    )

# ── horarios ─────────────────────────────────────────────
horarios = {}
weights = [7, 13, 11, 8, 5, 6, 12, 15, 14, 11, 8]
for h, w in zip(HORARIOS, weights):
    horarios[h] = w * random.randint(8, 15)

# ── metas (last 90 days) ─────────────────────────────────
metas = []
today = date(2026, 2, 28)
meta_mes_val = 85000
for i in range(59, -1, -1):
    d = today - timedelta(days=i)
    venda  = round(random.uniform(1800, 4500), 2)
    meta_d = round(meta_mes_val / 28, 2)
    metas.append(dict(
        data=str(d), venda=venda, meta_dia=meta_d,
        media_diaria=round(venda * random.uniform(0.85, 1.15), 2),
        acumulado=0, falta=0, projecao=0, meta_mes=meta_mes_val,
    ))

# ── assemble ─────────────────────────────────────────────
dashboard_data = dict(
    vendas_monthly=list(vm_map.values()),
    leads_monthly=leads_monthly,
    exp_monthly=exp_monthly,
    cancel_monthly=cancel_monthly,
    fin_monthly=fin_monthly,
    aulas_monthly=aulas_monthly,
    vendas_consultor_planos=vendas_consultor,
    exp_prof=exp_prof,
    metas=metas,
    cancelamentos_raw=cancelamentos_raw,
    financeiro_raw=financeiro_raw,
    horarios=horarios,
    vendas_fonte=list(vf_map.values()),
    _updated=datetime.now().isoformat() + 'Z',
)

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(dashboard_data, f, ensure_ascii=False)

print('data.json generated successfully.')
print(f'  Months: {len(MONTHS)}')
print(f'  Cancelamentos: {len(cancelamentos_raw)}')
print(f'  Financeiro raw: {len(financeiro_raw)}')
