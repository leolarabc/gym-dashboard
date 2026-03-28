#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gym Dashboard — Data Update Script
Reads data from Google Sheets via service account and generates data.json
"""

import json
import re
import os
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ── Configuration ──────────────────────────────────────────────
SPREADSHEET_ID       = 'YOUR_SPREADSHEET_ID_HERE'
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'service_account.json')
OUTPUT_FILE          = os.path.join(os.path.dirname(__file__), 'data.json')

# Sheet tab names — update to match your spreadsheet exactly
SHEETS = [
    'LEADS',
    'TRIAL SESSIONS',
    'SALES DETAIL',
    'MONTHLY TARGET',
    'CLASS LOG',
    'CANCELLATIONS',
    'FINANCIAL RECORDS',
]
# ──────────────────────────────────────────────────────────────


def get_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'],
    )
    return build('sheets', 'v4', credentials=creds, cache_discovery=False)


def range_to_rows(vr):
    if not vr or 'values' not in vr or len(vr['values']) < 2:
        return []
    values = vr['values']
    # Find the real header row (first row with 3+ non-empty cells)
    header_idx = 0
    for i, row in enumerate(values[:5]):
        if sum(1 for cell in row if str(cell).strip()) >= 3:
            header_idx = i
            break
    headers = [h.strip() for h in values[header_idx]]
    rows = []
    for row in values[header_idx + 1:]:
        obj = {headers[i]: (row[i] if i < len(row) else '') for i in range(len(headers))}
        rows.append(obj)
    return rows


def to_float(v):
    if v is None or v == '':
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    # Strip currency symbol and spaces first
    s = re.sub(r'[R$\s]', '', s)
    # Check for accounting notation: (1.000,00) = negative
    negative = s.startswith('(') and s.endswith(')')
    if negative:
        s = s[1:-1]
    s = s.replace('.', '').replace(',', '.')
    try:
        result = float(s)
        return -result if negative else result
    except ValueError:
        return 0.0


def to_date(v):
    if not v:
        return None
    v = str(v).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}', v):
        return v[:10]
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', v)
    if m:
        d, mo, y = m.groups()
        if len(y) == 2:
            y = '20' + y
        return f'{y}-{mo.zfill(2)}-{d.zfill(2)}'
    return None


def to_month(d):
    return d[:7] if d and len(d) >= 7 else None


def main():
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Starting update...')

    service = get_service()
    result = service.spreadsheets().values().batchGet(
        spreadsheetId=SPREADSHEET_ID,
        ranges=SHEETS,
    ).execute()

    vr = result.get('valueRanges', [])
    leads_raw  = range_to_rows(vr[0] if len(vr) > 0 else {})
    exp_raw    = range_to_rows(vr[1] if len(vr) > 1 else {})
    vendas_raw = range_to_rows(vr[2] if len(vr) > 2 else {})
    meta_raw   = range_to_rows(vr[3] if len(vr) > 3 else {})
    aulas_raw  = range_to_rows(vr[4] if len(vr) > 4 else {})
    cancel_raw = range_to_rows(vr[5] if len(vr) > 5 else {})
    fin_raw    = range_to_rows(vr[6] if len(vr) > 6 else {})

    print(f'  Leads: {len(leads_raw)} | Trials: {len(exp_raw)} | Sales: {len(vendas_raw)} | '
          f'Classes: {len(aulas_raw)} | Cancellations: {len(cancel_raw)} | Finance: {len(fin_raw)}')

    # ── 1. LEADS ────────────────────────────────────────────
    leads_monthly = {}
    for row in leads_raw:
        d = to_date(row.get('Date') or row.get('Data') or row.get('', ''))
        m = to_month(d)
        if not m or m < '2024':
            continue
        if m not in leads_monthly:
            leads_monthly[m] = dict(
                leads=0, exp_marcadas=0, exp_feitas=0, planos=0, valor=0,
                leads_online=0, exp_marcadas_online=0, exp_feitas_online=0, planos_online=0, valor_online=0,
                leads_offline=0, exp_marcadas_offline=0, exp_feitas_offline=0, planos_offline=0, valor_offline=0,
            )
        lm  = leads_monthly[m]
        # Adjust column names to match your spreadsheet headers
        lo  = to_float(row.get('Online Leads'))
        lf  = to_float(row.get('Offline Students')) + to_float(row.get('Referred Students'))
        mo_ = to_float(row.get('Online Trials Scheduled'))
        mf_ = to_float(row.get('Offline Trials Scheduled'))
        fo_ = to_float(row.get('Online Trials Done'))
        ff_ = to_float(row.get('Offline Trials Done'))
        po  = to_float(row.get('Online Plans Sold'))
        pf  = to_float(row.get('Offline Plans Sold'))
        vo  = to_float(row.get('Online Revenue'))
        vf  = to_float(row.get('Offline Revenue'))
        lm['leads']            += lo
        lm['exp_marcadas']     += mo_ + mf_
        lm['exp_feitas']       += fo_ + ff_
        lm['planos']           += po + pf
        lm['valor']            += vo + vf
        lm['leads_online']          += lo;  lm['exp_marcadas_online']  += mo_
        lm['exp_feitas_online']     += fo_; lm['planos_online']        += po;  lm['valor_online']   += vo
        lm['leads_offline']         += lf;  lm['exp_marcadas_offline'] += mf_
        lm['exp_feitas_offline']    += ff_; lm['planos_offline']       += pf;  lm['valor_offline']  += vf

    # ── 2. TRIAL SESSIONS ───────────────────────────────────
    exp_monthly, exp_prof = {}, {}
    for row in exp_raw:
        d = to_date(row.get('DATE', '') or row.get('Data', ''))
        m = to_month(d)
        if not m or m < '2024':
            continue
        if m not in exp_monthly:
            exp_monthly[m] = dict(total=0, fechou=0, nao_fechou=0, valor=0,
                                  por_fonte={}, por_prof={}, por_aula={})
        em     = exp_monthly[m]
        fechou = 'yes' in str(row.get('SIGNED UP', '')).lower() or \
                 'fechou' in str(row.get('FECHOU PLANO', '')).lower()
        val    = to_float(row.get('VALUE') or row.get('VALOR'))
        em['total'] += 1
        if fechou:
            em['fechou'] += 1; em['valor'] += val
        else:
            em['nao_fechou'] += 1
        for field, key in [('SOURCE', 'por_fonte'), ('INSTRUCTOR', 'por_prof'), ('CLASS TYPE', 'por_aula')]:
            k = str(row.get(field) or 'N/A').strip()
            em[key][k] = em[key].get(k, 0) + 1
        prof = str(row.get('INSTRUCTOR') or row.get('PROFESSOR') or 'N/A').strip()
        if prof not in exp_prof:
            exp_prof[prof] = dict(total=0, fechou=0, valor=0)
        exp_prof[prof]['total'] += 1
        if fechou:
            exp_prof[prof]['fechou'] += 1; exp_prof[prof]['valor'] += val

    # ── 3. SALES ────────────────────────────────────────────
    vm_map, vf_map, vendas_consultor_planos = {}, {}, {}
    for row in vendas_raw:
        d = to_date(row.get('DATE', '') or row.get('DATA', ''))
        m = to_month(d)
        if not m or m < '2024':
            continue
        cat       = str(row.get('CATEGORY') or row.get('CATEGORIA') or '').strip()
        val       = to_float(row.get('VALUE') or row.get('VALOR'))
        fonte     = str(row.get('SOURCE') or row.get('FONTE') or 'N/A').strip()
        consultor = str(row.get('CONSULTANT') or row.get('CONSULTOR') or 'N/A').strip()
        vm_key = f'{m}|{cat}'
        if vm_key not in vm_map:
            vm_map[vm_key] = dict(mes=m, categoria=cat, count=0, valor=0)
        vm_map[vm_key]['count'] += 1; vm_map[vm_key]['valor'] += val
        vf_key = f'{m}|{fonte}'
        if vf_key not in vf_map:
            vf_map[vf_key] = dict(mes=m, fonte=fonte, count=0, valor=0)
        vf_map[vf_key]['count'] += 1; vf_map[vf_key]['valor'] += val
        if cat not in ('PRODUCT', 'SINGLE CLASS', 'PRODUTO', 'AULA'):
            if consultor not in vendas_consultor_planos:
                vendas_consultor_planos[consultor] = dict(count=0, valor=0)
            vendas_consultor_planos[consultor]['count'] += 1
            vendas_consultor_planos[consultor]['valor'] += val

    # ── 4. MONTHLY TARGET ───────────────────────────────────
    metas = []
    for row in meta_raw:
        d = to_date(row.get('') or row.get('Date') or row.get('Data', ''))
        if not d:
            continue
        metas.append(dict(
            data=d,
            venda=to_float(row.get('SALES') or row.get('VENDA')),
            meta_dia=to_float(row.get('DAILY TARGET') or row.get('META DIA')),
            media_diaria=to_float(row.get('DAILY AVG') or row.get('MÉDIA DIÁRIA')),
            acumulado=to_float(row.get('ACCUMULATED') or row.get('ACUMULADO')),
            falta=to_float(row.get('REMAINING') or row.get('FALTA')),
            projecao=to_float(row.get('PROJECTION') or row.get('PROJEÇÃO')),
            meta_mes=to_float(row.get('MONTHLY TARGET') or row.get('META') or 0),
        ))

    # ── 5. CLASS LOG ────────────────────────────────────────
    aulas_monthly, horarios = {}, {}
    for row in aulas_raw:
        d = to_date(row.get('DATE', '') or row.get('DATA', ''))
        m = to_month(d)
        if not m or m < '2024':
            continue
        if m not in aulas_monthly:
            aulas_monthly[m] = dict(total=0, ocupacao_total=0,
                                    por_prof={}, por_modalidade={}, por_arena={})
        am   = aulas_monthly[m]
        ocup = to_float(row.get('OCCUPANCY') or row.get('OCUPAÇÃO'))
        am['total'] += 1; am['ocupacao_total'] += ocup
        prof = str(row.get('INSTRUCTOR') or row.get('PROFESSOR') or 'N/A').strip()
        if prof not in am['por_prof']:
            am['por_prof'][prof] = dict(aulas=0, ocupacao=0)
        am['por_prof'][prof]['aulas'] += 1; am['por_prof'][prof]['ocupacao'] += ocup
        mod = str(row.get('CLASS TYPE') or row.get('MODALIDADE') or 'N/A').strip()
        if mod not in am['por_modalidade']:
            am['por_modalidade'][mod] = dict(aulas=0, ocupacao=0)
        am['por_modalidade'][mod]['aulas'] += 1; am['por_modalidade'][mod]['ocupacao'] += ocup
        arena = str(row.get('ARENA') or row.get('ROOM') or 'N/A').strip()
        am['por_arena'][arena] = am['por_arena'].get(arena, 0) + 1
        h = str(row.get('TIME') or row.get('HORARIO') or '').strip()
        if h:
            horarios[h] = horarios.get(h, 0) + 1

    # ── 6. CANCELLATIONS ────────────────────────────────────
    cancel_monthly, cancelamentos_raw = {}, []
    for row in cancel_raw:
        d = to_date(row.get('') or row.get('Date') or row.get('Data', ''))
        m = to_month(d)
        if not m or m < '2024':
            continue
        val    = to_float(row.get('REFUND') or row.get('VALOR A DEVOLVER'))
        tipo   = str(row.get('TYPE') or row.get('TIPO') or 'N/A').strip()
        motivo = str(row.get('REASON') or row.get('MOTIVO') or 'N/A').strip()
        nome   = str(row.get('NAME') or row.get('NOME') or '').strip()
        if m not in cancel_monthly:
            cancel_monthly[m] = dict(total=0, valor=0, por_tipo={}, por_motivo={})
        cancel_monthly[m]['total'] += 1; cancel_monthly[m]['valor'] += val
        cancel_monthly[m]['por_tipo'][tipo]     = cancel_monthly[m]['por_tipo'].get(tipo, 0) + 1
        cancel_monthly[m]['por_motivo'][motivo] = cancel_monthly[m]['por_motivo'].get(motivo, 0) + 1
        cancelamentos_raw.append(dict(data=d, nome=nome, valor=val, tipo=tipo, motivo=motivo))

    # ── 7. FINANCIAL RECORDS ────────────────────────────────
    fin_monthly, financeiro_raw = {}, []
    for row in fin_raw:
        d = to_date(row.get('DATE', '') or row.get('DATA', ''))
        m = to_month(d)
        if not m or m < '2024':
            continue
        val    = to_float(row.get('VALUE') or row.get('VALOR'))
        pc     = str(row.get('ACCOUNT') or row.get('PLANO DE CONTAS') or 'N/A').strip()
        desc   = str(row.get('DESCRIPTION') or row.get('DESCRIÇÃO') or '').strip()
        status = str(row.get('STATUS') or '').strip()
        if m not in fin_monthly:
            fin_monthly[m] = dict(receitas=0, despesas=0, por_conta={})
        if val > 0:
            fin_monthly[m]['receitas'] += val
        else:
            fin_monthly[m]['despesas'] += abs(val)
        fin_monthly[m]['por_conta'][pc] = fin_monthly[m]['por_conta'].get(pc, 0) + val
        financeiro_raw.append(dict(data=d, descricao=desc, plano_contas=pc, valor=val, status=status))

    # ── Save ─────────────────────────────────────────────────
    dashboard_data = dict(
        vendas_monthly=list(vm_map.values()),
        leads_monthly=leads_monthly,
        exp_monthly=exp_monthly,
        cancel_monthly=cancel_monthly,
        fin_monthly=fin_monthly,
        aulas_monthly=aulas_monthly,
        vendas_consultor_planos=vendas_consultor_planos,
        exp_prof=exp_prof,
        metas=metas,
        cancelamentos_raw=cancelamentos_raw,
        financeiro_raw=financeiro_raw,
        horarios=horarios,
        vendas_fonte=list(vf_map.values()),
        _updated=datetime.now().isoformat() + 'Z',
    )

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False)

    print(f'  data.json saved to {OUTPUT_FILE}')
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] Done.')


if __name__ == '__main__':
    main()
