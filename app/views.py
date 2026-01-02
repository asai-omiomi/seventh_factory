from django.shortcuts import render, redirect,get_object_or_404
from django.views.generic.base import TemplateView
from .models import CustomerModel,CustomerRecordModel,StaffModel,CustomerWorkStatusPatternModel,StaffRecordModel, StaffSessionRecordModel,StaffWorkStatusPatternModel,CustomerSessionRecordModel,CustomerSessionPatternModel,TransportPatternModel,StaffSessionPatternModel,TransportRecordModel,WeekdayEnum, PlaceModel,TransportMeansEnum,TransportTypeEnum,StaffWorkStatusEnum, CustomerWorkStatusEnum,  WORK_SESSION_COUNT, PlaceRemarksModel
from .forms import CustomerWorkStatusPatternForm,PlaceRemarksForm,StaffForm,StaffRecordForm,CustomerForm,CustomerWorkStatusPatternForm,CustomerSessionPatternForm,CustomerSessionRecordForm,StaffSessionRecordForm,TransportPatternForm,TransportRecordForm,StaffSessionPatternForm,CustomerRecordForm,StaffWorkStatusPatternForm,CalendarForm,OutputForm
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse
from django.urls import reverse
import csv
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from collections import defaultdict

class IndexView(TemplateView):
    template_name = 'app/index.html'

def info_today(request):
    work_date = datetime.now().date()

    return redirect('info', work_date)

def info(request, work_date):
    # =========================
    # POST：勤務状態の更新
    # =========================
    # if request.method == "POST" and "update_current_status" in request.POST:
    #     customer_id = request.POST.get("update_current_status")
    #     work_date = request.POST.get("work_date")
    #     new_status = request.POST.get("current_status")

    #     customer_record = get_object_or_404(
    #         CustomerRecordModel,
    #         customer__pk=customer_id,
    #         work_date=work_date
    #     )

    #     customer_record.current_status = int(new_status)
    #     customer_record.save()

    # =========================
    # GET：通常の表示
    # =========================
    calendar_form = CalendarForm(initial_date=work_date)

    info = _build_info(work_date)

    transport_table_rows = _build_transport_table_rows(work_date)

    return render(request,'app/info.html',{
        'work_date':work_date,
        'calendar_form':calendar_form,
        'info': info,
        'transport_table_rows': transport_table_rows,
        # 'current_status_choices': CurrentStatusEnum.choices, 
        })

def _build_info(work_date):

    staff_records = StaffRecordModel.objects.filter(work_date=work_date).order_by('staff__order')

    customer_records = CustomerRecordModel.objects.filter(work_date=work_date).order_by('customer__order')

    if not staff_records and not customer_records:
        return []

    info = []

    # 勤務地別を追加
    _append_place_info(staff_records, customer_records, work_date, info)
    # 在宅を追加
    _append_home_info(customer_records, info)
    # 休みを追加
    _append_off_info(staff_records, customer_records, info)

    return info

def _append_place_info(staff_records, customer_records, work_date, info):
    places = PlaceModel.objects.all()

    for place in places:
        staff_list = _bulid_staff_list(staff_records, place)    
        customer_list = _build_customer_list(customer_records, place)  
        staff_customer_list = _build_staff_customer_list(staff_list, customer_list)
        remarks = _build_remarks(place, work_date)

        info.append({
            'place_id': place.id,
            'place_name': place.name,
            'color': "table-secondary",
            'staff_cusotmer_list': staff_customer_list,
            'remarks': remarks,
        })  

def _append_home_info(customer_records, info):

    customer_list = _build_customer_list(customer_records, None, CustomerWorkStatusEnum.HOME)
    staff_cusotmer_list = _build_staff_customer_list(None, customer_list)
    
    info.append({
        'place_id': -1,
        'place_name': "在宅",
        'color': "table-success",
        'staff_cusotmer_list': staff_cusotmer_list,
        'remarks': "",
    })     

def _append_off_info(staff_works, customer_records, info):

    staff_list = _bulid_staff_list(staff_works, None, StaffWorkStatusEnum.OFF) # 有休も
    customer_list = _build_customer_list(customer_records, None, CustomerWorkStatusEnum.OFF)
    staff_cusotmer_list = _build_staff_customer_list(staff_list, customer_list)

    info.append({
        'place_id': -1,
        'place_name': "休み",
        'color': "table-danger",
        'staff_cusotmer_list': staff_cusotmer_list,
        'remarks': "",
    })  

# def _status_btn_class(status):
#     return {
#         CurrentStatusEnum.BEFORE:   "btn-outline-primary",
#         CurrentStatusEnum.WORKING:  "btn-primary",
#         CurrentStatusEnum.FINISHED: "btn-secondary",
#         CurrentStatusEnum.HOME:     "btn-success",
#         CurrentStatusEnum.ABSENT:   "btn-danger",
#     }.get(status, "btn-outline-secondary")

def _build_member_list(
    records,
    place,
    work_status,
    get_member,              # rcd → customer / staff
    session_model,           
    extra_lines_builder=None # 追加表示（送迎など）
):
    if not place:
        return [
            {
                'id': member.id,
                'name': member.name,
                'display': member.name,
            }
            for rcd in records
            if (member := get_member(rcd)) and rcd.work_status == work_status
        ]

    result = []

    for rcd in records:
        member = get_member(rcd)
        if not member:
            continue

        # 勤務セッション（place に一致するもの）
        sessions = session_model.objects.filter(
            record=rcd,
            place=place,
        )

        if not sessions.exists():
            continue

        lines = [member.name]

        # 勤務時間
        for s in sessions.order_by('session_no'):
            if s.start_time and s.end_time:
                lines.append(
                    f"{s.start_time.strftime('%H:%M')}～{s.end_time.strftime('%H:%M')}"
                )

        # 追加情報（送迎など）
        if extra_lines_builder:
            lines.extend(extra_lines_builder(rcd))

        result.append({
            'id': member.id,
            'name': member.name,
            'display': "\n".join(lines),
        })

    return result

def _build_customer_extra_lines(rcd):
    lines = []

    for label, t_type in (
        ("朝", TransportTypeEnum.MORNING),
        ("帰り", TransportTypeEnum.RETURN),
    ):
        transport = TransportRecordModel.objects.filter(
            record=rcd,
            transport_type=t_type
        ).first()

        if not transport:
            continue

        text = f"[{label}] {transport.get_transport_means_display() or ''}"

        if transport.transport_means == TransportMeansEnum.TRANSFER:
            if transport.staff:
                text += f" {transport.staff}"
            if transport.place:
                text += f" {transport.place}"
            if transport.time:
                text += f" {transport.time.strftime('%H:%M')}"

        lines.append(text)

    return lines

def _bulid_staff_list(staff_records, place, work_status=None):
    return _build_member_list(
        records=staff_records,
        place=place,
        work_status=work_status,
        get_member=lambda rcd: rcd.staff,
        session_model=StaffSessionRecordModel,
    ) 

def _build_customer_list(customer_records, place, work_status=None):
    return _build_member_list(
        records=customer_records,
        place=place,
        work_status=work_status,
        get_member=lambda rcd: rcd.customer,
        session_model=CustomerSessionRecordModel,
        extra_lines_builder=_build_customer_extra_lines,
    )
    
def _build_remarks(place=None, work_date=None):
    if place:
        qs = PlaceRemarksModel.objects.filter(place=place, work_date=work_date)
        if qs.exists():
            prmks = qs[0]  # querysetの先頭を取得
            return prmks.remarks or "　"
        else:
            return "　"
    else:
        return ""


def _build_staff_customer_list(staff_list, customer_list):
    
    # None の場合は空リストに置き換える
    staff_list = staff_list or []
    customer_list = customer_list or []

    staff_customer_list = []
    max_length = max(len(staff_list), len(customer_list))

    for i in range(max_length):
        staff = staff_list[i] if i < len(staff_list) else None
        customer = customer_list[i] if i < len(customer_list) else None
        staff_customer_list.append((staff, customer))

    return staff_customer_list

def _build_transport_table_rows(work_date):
    transports = (
        TransportRecordModel.objects
        .filter(record__work_date=work_date, transport_means=TransportMeansEnum.TRANSFER)
        .select_related('staff', 'customer')
        .order_by('staff__order', 'customer__order')
    )

    rows = {}

    for t in transports:
        staff_id = t.staff_id

        if staff_id not in rows:
            rows[staff_id] = {
                'staff': t.staff,
                'morning_list': [],
                'return_list': [],
            }

        text = _format_transport(t)

        if t.transport_type == TransportTypeEnum.MORNING:
            rows[staff_id]['morning_list'].append(text)

        elif t.transport_type == TransportTypeEnum.RETURN:
            rows[staff_id]['return_list'].append(text)

    # 表示用文字列に変換
    for row in rows.values():
        row['morning_text'] = '<br>'.join(row['morning_list']) or 'ー'
        row['return_text'] = '<br>'.join(row['return_list']) or 'ー'

    return rows.values()

def _format_transport(t):
    parts = [
        t.customer.name,
        t.time.strftime('%H:%M') if t.time else '',
        t.place or '',
    ]
    return ' '.join(p for p in parts if p)

def info_dispatch(request, work_date):
    assert request.method == 'POST'
    change_date = request.POST.get('change_date')
    create_records = request.POST.get('create_records')
    edit_place_remarks = request.POST.get('edit_place_remarks')
    customer_record_edit = request.POST.get('customer_record_edit')
    staff_record_edit = request.POST.get('staff_record_edit')
   
    if change_date:
        work_date = request.POST.get('date')
        return redirect('info', work_date)
    elif create_records:
        work_date = request.POST.get('date')
        _create_records(work_date)
        return redirect('info', work_date)
    elif edit_place_remarks:
        place_id = edit_place_remarks
        return redirect('place_remarks', place_id, work_date)
    elif customer_record_edit:
        customer_id = customer_record_edit
        return redirect('customer_record_edit', 
            customer_id=customer_id, work_date=work_date)    
    elif staff_record_edit:
        staff_id = staff_record_edit
        return redirect('staff_record_edit', 
            staff_id=staff_id, work_date=work_date)   
    
    return redirect('info', work_date)     

def _create_records(work_date):

    # staff
    _create_records_from_pattern_common(
        work_date=work_date,
        owner_model=StaffModel,
        record_model=StaffRecordModel,
        owner_field='staff',
        work_status_pattern_model=StaffWorkStatusPatternModel,
        off_value=StaffWorkStatusEnum.OFF,
        session_pattern_model=StaffSessionPatternModel,
        session_record_model=StaffSessionRecordModel,
        with_transport=False,
    )

    # customer
    _create_records_from_pattern_common(
        work_date=work_date,
        owner_model=CustomerModel,
        record_model=CustomerRecordModel,
        owner_field='customer',
        work_status_pattern_model=CustomerWorkStatusPatternModel,
        off_value=CustomerWorkStatusEnum.OFF,
        session_pattern_model=CustomerSessionPatternModel,
        session_record_model=CustomerSessionRecordModel,
        with_transport=True,
    )

def _create_work_sessions_from_pattern_common(
    *,
    record,
    owner_field,
    pattern_model,
    session_record_model,
):
    owner = getattr(record, owner_field)

    patterns = pattern_model.objects.filter(
        **{
            owner_field: owner,
            'weekday': _get_day(record.work_date),
        }
    )

    if not patterns.exists():
        return

    with transaction.atomic():
        for ptn in patterns:
            session_record_model.objects.update_or_create(
                record=record,
                session_no=ptn.session_no,
                defaults={
                    'place': ptn.place,
                    'start_time': ptn.start_time,
                    'end_time': ptn.end_time,
                }
            )

def _get_day(work_date):
    if isinstance(work_date, str):
        work_date = datetime.strptime(work_date, "%Y-%m-%d").date()
    return work_date.weekday() + 1

def _resolve_work_status_common(
    *,
    owner,
    work_date,
    pattern_model,
    owner_field,
    off_value,
):
    pattern = pattern_model.objects.filter(
        **{
            owner_field: owner,
            'weekday': _get_day(work_date),
        }
    ).first()

    return pattern.work_status if pattern else off_value


def _create_transports_from_pattern(customer_record, transport_type):
    pattern = TransportPatternModel.objects.filter(
        customer=customer_record.customer,
        weekday=_get_day(customer_record.work_date),
        transport_type = transport_type
    ).first()

    if not pattern:
        # パターンがない場合は何もしない
        return

    with transaction.atomic():
        obj, created = TransportRecordModel.objects.update_or_create(
            customer = customer_record.customer,
            record=customer_record,
            transport_type = transport_type,
            defaults={
                'transport_means': pattern.transport_means,
                'place': pattern.place,
                'staff': pattern.staff,
                'time': pattern.time,
            }
        )    
def _create_records_from_pattern_common(
    *,
    work_date,
    owner_model,
    record_model,
    owner_field,
    work_status_pattern_model,
    off_value,
    session_pattern_model,
    session_record_model,
    with_transport=False,
    order_field='order',
):
    owners = owner_model.objects.all().order_by(order_field)

    for owner in owners:
        _create_record_from_pattern_common(
            owner=owner,
            work_date=work_date,
            record_model=record_model,
            owner_field=owner_field,
            work_status_pattern_model=work_status_pattern_model,
            off_value=off_value,
            session_pattern_model=session_pattern_model,
            session_record_model=session_record_model,
            with_transport=with_transport,
        )

def _create_record_from_pattern_common(
    *,
    owner,
    work_date,
    record_model,
    owner_field,
    work_status_pattern_model,
    off_value,
    session_pattern_model,
    session_record_model,
    with_transport=False,
):
    with transaction.atomic():
        # 勤務ステータス解決
        work_status = _resolve_work_status_common(
            owner=owner,
            work_date=work_date,
            pattern_model=work_status_pattern_model,
            owner_field=owner_field,
            off_value=off_value,
        )

        # レコード作成 or 更新
        rcd, created = record_model.objects.update_or_create(
            **{
                owner_field: owner,
                'work_date': work_date,
            },
            defaults={
                'work_status': work_status,
            }
        )

        # 勤務セッション作成
        _create_work_sessions_from_pattern_common(
            record=rcd,
            owner_field=owner_field,
            pattern_model=session_pattern_model,
            session_record_model=session_record_model,
        )

        # 送迎（必要な場合のみ）
        if with_transport:
            _create_transports_from_pattern(rcd, TransportTypeEnum.MORNING)
            _create_transports_from_pattern(rcd, TransportTypeEnum.RETURN)

    return rcd

def _customer_extra_context(record):
    return {
        'morning_transport_form': _build_transport_form(
            record,
            TransportTypeEnum.MORNING,
            prefix=_transport_prefix(TransportTypeEnum.MORNING),
            form_class=TransportRecordForm,
            is_record=True
        ),
        'return_transport_form': _build_transport_form(
            record,
            TransportTypeEnum.RETURN,
            prefix=_transport_prefix(TransportTypeEnum.RETURN),
            form_class=TransportRecordForm,
            is_record=True
        ),
    }

def _record_edit_common(
    request,
    *,
    member_id,
    work_date,
    member_model,
    record_model,
    record_form_class,
    session_model,
    session_form_class,
    template_name,
    form_action_name,
    member_field,            # 'staff' or 'customer'
    extra_context_builder=None,
):
    member = get_object_or_404(member_model, pk=member_id)

    record, created = record_model.objects.get_or_create(
        **{
            member_field: member,
            'work_date': work_date,
        }
    )

    record_form = record_form_class(instance=record)

    existing_sessions = list(
        session_model.objects
        .filter(record=record)
        .order_by('session_no')
    )

    session_forms = _build_session_forms(
        existing_sessions,
        form_class=session_form_class,
        prefix_func=lambda i: _session_index_prefix(i)
    )

    form_action = reverse(
        form_action_name,
        kwargs={
            f'{member_field}_id': member_id,
            'work_date': work_date,
        }
    )

    context = {
        f'{member_field}_id': member_id,
        f'{member_field}_name': member.name,
        'work_date': work_date,
        'record_form': record_form,
        'session_forms': session_forms,
        'transfer_value': TransportMeansEnum.TRANSFER,
        'form_action': form_action,
    }

    if extra_context_builder:
        context.update(extra_context_builder(record))

    return render(request, template_name, context)



#################################################
# 情報画面のスタッフの編集ボタンを押したときの処理
# スタッフ実績の編集画面を表示する
################################################
def staff_record_edit(request, staff_id, work_date):

    return _record_edit_common(
            request,
            member_id=staff_id,
            work_date=work_date,
            member_model=StaffModel,
            record_model=StaffRecordModel,
            record_form_class=StaffRecordForm,
            session_model=StaffSessionRecordModel,
            session_form_class=StaffSessionRecordForm,
            template_name='app/staff_record_edit.html',
            form_action_name=staff_record_save,
            member_field='staff',
        )
    # staff = get_object_or_404(StaffModel, pk=staff_id)

    # record, created = StaffRecordModel.objects.get_or_create(
    #     staff=staff,
    #     work_date=work_date,
    # ) 

    # record_form = StaffRecordForm(
    #     instance = record
    # )

    # # 勤務セッションフォーム
    # existing_sessions = list(StaffSessionRecordModel.objects.filter(
    #     record = record,
    #     ).order_by('session_no'))
    
    # session_forms = _build_session_forms(
    #     existing_sessions,
    #     form_class=StaffSessionRecordForm,
    #     prefix_func=lambda i: _session_index_prefix(i)
    # )

    # form_action = reverse(
    #     staff_record_save,
    #     kwargs={
    #         'staff_id': staff_id, 
    #         'work_date' : work_date
    #         }
    # )    

    # return render(request, 'app/staff_record_edit.html', {
    #         'staff_id': staff_id,
    #         'staff_name':staff.name,
    #         'work_date': work_date,
    #         'record_form': record_form,
    #         'session_forms':session_forms,
    #         'transfer_value': TransportMeansEnum.TRANSFER,
    #         'form_action':form_action,
    #     })

       
#################################################
# 情報画面の利用者の編集ボタンを押したときの処理
# 利用者実績の編集画面を表示する
################################################
def customer_record_edit(request, customer_id, work_date):
    return _record_edit_common(
            request,
            member_id=customer_id,
            work_date=work_date,
            member_model=CustomerModel,
            record_model=CustomerRecordModel,
            record_form_class=CustomerRecordForm,
            session_model=CustomerSessionRecordModel,
            session_form_class=CustomerSessionRecordForm,
            template_name='app/customer_record_edit.html',
            form_action_name=customer_record_save,
            member_field='customer',
            extra_context_builder=_customer_extra_context,
        )
    # customer = get_object_or_404(CustomerModel, pk=customer_id)

    # record, created = CustomerRecordModel.objects.get_or_create(
    #     customer=customer,
    #     work_date=work_date,
    # ) 

    # record_form = CustomerRecordForm(
    #     instance = record
    # )

    # # 勤務セッションフォーム
    # existing_sessions = list(CustomerSessionRecordModel.objects.filter(
    #     record = record,
    #     ).order_by('session_no'))
    
    # session_forms = _build_session_forms(
    #     existing_sessions,
    #     form_class=CustomerSessionRecordForm,
    #     prefix_func=lambda i: _session_index_prefix(i)
    # )

    # # 送迎フォーム
    # morning_transport_form = _build_transport_form(
    #     record, TransportTypeEnum.MORNING,
    #     prefix=_transport_prefix(TransportTypeEnum.MORNING),
    #     form_class=TransportRecordForm,
    #     is_record=True
    # )

    # return_transport_form = _build_transport_form(
    #     record, TransportTypeEnum.RETURN,
    #     prefix=_transport_prefix(TransportTypeEnum.RETURN),
    #     form_class=TransportRecordForm,
    #     is_record=True
    # )

    # form_action = reverse(
    #     customer_record_save,
    #     kwargs={
    #         'customer_id': customer_id, 
    #         'work_date' : work_date
    #         }
    # )    

    # return render(request, 'app/customer_record_edit.html', {
    #         'customer_id': customer_id,
    #         'customer_name':customer.name,
    #         'work_date': work_date,
    #         'record_form': record_form,
    #         'session_forms':session_forms,
    #         'morning_transport_form':morning_transport_form,
    #         'return_transport_form':return_transport_form,
    #         'transfer_value': TransportMeansEnum.TRANSFER,
    #         'form_action':form_action,
    #     })


def _build_session_forms(existing_sessions, form_class, prefix_func):
    session_forms = []

    for i in range(WORK_SESSION_COUNT):
        if i < len(existing_sessions):
            session_instance = existing_sessions[i]
        else:
            session_instance = None

        form = form_class(
            instance=session_instance,
            prefix=prefix_func(i),
            initial={'session_no': i + 1} if session_instance is None else None
        )

        session_forms.append(form)

    return session_forms


#################################################
# スタッフ実績画面でボタン(保存/キャンセル)を
# 押したときの処理
################################################
def staff_record_save(request, staff_id, work_date):     
    assert request.method == 'POST'

    action = request.POST.get('action')

    if action == 'save':
        staff = get_object_or_404(StaffModel, pk=staff_id)

        StaffRecordModel.objects.get_or_create(staff=staff, work_date=work_date)

        record_form = StaffRecordForm(request.POST)  

        if record_form.is_valid():
            record, created = StaffRecordModel.objects.update_or_create(
                staff=staff,
                work_date=work_date,
                defaults=record_form.cleaned_data
            )   

        # 勤務セッションを保存
        for i in range(WORK_SESSION_COUNT):
            session_form = StaffSessionRecordForm(
                request.POST,
                prefix=_session_index_prefix(i)
            )

            if not session_form.is_valid():
                continue  # 入力がないフォームは無視

            cd = session_form.cleaned_data

            StaffSessionRecordModel.objects.update_or_create(
                record=record,  
                session_no=i + 1,
                defaults={            
                    'place': cd['place'],
                    'start_time': cd['start_time'],
                    'end_time': cd['end_time'],
                }
            )

    return redirect('info', work_date)

#################################################
# 利用者実績画面でボタン(保存/キャンセル)を
# 押したときの処理
################################################
def customer_record_save(request, customer_id, work_date):   
    assert request.method == 'POST'

    action = request.POST.get('action')

    if action == 'save':
        customer = get_object_or_404(CustomerModel, pk=customer_id)

        CustomerRecordModel.objects.get_or_create(customer=customer, work_date=work_date)

        record_form = CustomerRecordForm(request.POST)  

        if record_form.is_valid():
            record, created = CustomerRecordModel.objects.update_or_create(
                customer=customer,
                work_date=work_date,
                defaults=record_form.cleaned_data
            )   

        # 勤務セッションを保存
        for i in range(WORK_SESSION_COUNT):
            session_form = CustomerSessionRecordForm(
                request.POST,
                prefix=_session_index_prefix(i)
            )

            if not session_form.is_valid():
                continue  # 入力がないフォームは無視

            cd = session_form.cleaned_data

            CustomerSessionRecordModel.objects.update_or_create(
                record=record,  
                session_no=i + 1,
                defaults={            
                    'place': cd['place'],
                    'start_time': cd['start_time'],
                    'end_time': cd['end_time'],
                }
            )

        # 送迎を保存
        _save_transport_record(request, record, TransportTypeEnum.MORNING)
        _save_transport_record(request, record, TransportTypeEnum.RETURN)

    return redirect('info', work_date)

def _save_transport_record(request, record, transport_type):

    form = TransportRecordForm(
        request.POST,
        transport_type=transport_type,
        prefix=_transport_prefix(transport_type)
    )

    if not form.is_valid():
        print(form.errors)
        return False

    cd = form.cleaned_data

    TransportRecordModel.objects.update_or_create(
        customer=record.customer,
        record = record,
        transport_type=transport_type,
        defaults={
            'transport_means': cd['transport_means'],
            'place': cd['place'],
            'staff': cd['staff'],
            'time': cd['time'],
        }
    )

    return True

def place_remarks_edit(request, place_id, work_date):
    place = PlaceModel.objects.get(pk=place_id)

    place_remarks, created = PlaceRemarksModel.objects.get_or_create(
        place=place, 
        work_date=work_date,
    )

    form = PlaceRemarksForm(instance=place_remarks)

    return render(
        request, 
        'app/place_remarks.html',
        {
            'form':form,
            'place':place,
            'work_date':work_date,
            'place_remarks': place_remarks,
        })

def place_remarks_save(request, place_id, work_date):
    assert request.method == 'POST'    

    action = request.POST.get('action')

    if action == 'cancel':
        return

    place = get_object_or_404(PlaceModel, pk=place_id)

    place_remarks, created = PlaceRemarksModel.objects.get_or_create(
        place=place,
        work_date=work_date,
        defaults={'remarks': ''}
    )

    form = PlaceRemarksForm(request.POST, instance=place_remarks)
        
    if form.is_valid():
        place_remarks.save()

    return redirect('info', work_date=work_date)

def _list_dispatch(request, kind):
    assert request.method == 'POST'

    create = request.POST.get('create')
    up = request.POST.get('up')
    down = request.POST.get('down')
    edit = request.POST.get('edit')
    
    create_url = f'{kind}_create'
    list_url   = f'{kind}_list'
    edit_url   = f'{kind}_edit'
    id_field = f'{kind}_id'

    if create:
        return redirect(create_url)
    elif up:
        MOVE_UP_FUNCS[kind](up)
        return redirect(list_url)
    elif down:
        MOVE_DOWN_FUNCS[kind](down)
        return redirect(list_url)
    elif edit:
        return redirect(edit_url, **{id_field: edit})
    return redirect(list_url)    

def staff_list_dispatch(request):
    return _list_dispatch(request, kind='staff') 

def staff_list(request):
    staffs = StaffModel.objects.all().order_by('order')
    return render(request, 'app/staff_list.html',{'staffs':staffs})

def _move_order_up(model, pk):
    obj = get_object_or_404(model, pk=pk)

    prev_obj = model.objects.filter(
        order__lt=obj.order
    ).order_by('-order').first()

    if not prev_obj:
        return

    obj.order, prev_obj.order = prev_obj.order, obj.order
    obj.save()
    prev_obj.save()

def _move_order_down(model, pk):
    obj = get_object_or_404(model, pk=pk)

    next_obj = model.objects.filter(
        order__gt=obj.order
    ).order_by('order').first()

    if not next_obj:
        return

    obj.order, next_obj.order = next_obj.order, obj.order
    obj.save()
    next_obj.save()

def staff_create(request):
    return _create_or_edit_staff(request)

def staff_edit(request,staff_id):
    return _create_or_edit_staff(request, staff_id)

def _create_or_edit_common(
    *,
    request,
    owner_id,
    owner_model,
    owner_form_class,
    build_patterns_kwargs,
    save_url_name,
    id_kwarg_name,
    template_name,
    context_name,
):
    owner = (
        get_object_or_404(owner_model, id=owner_id)
        if owner_id else owner_model()
    )

    form = owner_form_class(instance=owner)

    day_patterns = _build_patterns(
        owner=owner,
        **build_patterns_kwargs
    )

    owner_id_value = owner.id if owner.pk else 0

    form_action = reverse(
        save_url_name,
        kwargs={id_kwarg_name: owner_id_value}
    )

    return render(request, template_name, {
        context_name: form,
        'day_patterns': day_patterns,
        id_kwarg_name: owner_id_value,
        'form_action': form_action,
        'transfer_value': TransportMeansEnum.TRANSFER,
    })


def _create_or_edit_staff(request, staff_id=None):
    return _create_or_edit_common(
        request=request,
        owner_id=staff_id,
        owner_model=StaffModel,
        owner_form_class=StaffForm,
        build_patterns_kwargs=dict(
            work_status_pattern_model=StaffWorkStatusPatternModel,
            work_status_pattern_form=StaffWorkStatusPatternForm,
            session_pattern_model=StaffSessionPatternModel,
            session_form_class=StaffSessionPatternForm,
            owner_field='staff',
        ),
        save_url_name='staff_save',
        id_kwarg_name='staff_id',
        template_name='app/staff_edit.html',
        context_name='staff_form',
    )

def _build_patterns(
    *,
    owner,
    work_status_pattern_model,
    work_status_pattern_form,
    session_pattern_model,
    session_form_class,
    owner_field,
    extra_builder=None,
):
    day_patterns = []

    for day in WeekdayEnum:
        # 勤務ステータス
        work_status_form = _build_work_status(
            owner=owner,
            day_value=day.value,
            pattern_model=work_status_pattern_model,
            owner_field=owner_field,
            form_class=work_status_pattern_form,
        )

        # セッション
        if owner.pk:
            existing_sessions = list(
                session_pattern_model.objects.filter(
                    **{owner_field: owner, 'weekday': day.value}
                ).order_by('session_no')
            )
        else:
            existing_sessions = [None] * WORK_SESSION_COUNT

        session_forms = _build_session_forms(
            existing_sessions,
            form_class=session_form_class,
            prefix_func=lambda i, dv=day.value: _session_prefix(dv, i)
        )

        pattern = {
            'value': day.value,
            'label': day.label,
            'work_status_form': work_status_form,
            'session_forms': session_forms,
        }

        # customer 専用（送迎など）
        if extra_builder:
            pattern.update(extra_builder(owner, day.value))

        day_patterns.append(pattern)

    return day_patterns

def _build_customer_extra(customer, day_value):
    return {
        'morning_transport_form': _build_transport_form(
            customer,
            TransportTypeEnum.MORNING,
            prefix=_transport_day_prefix(day_value, TransportTypeEnum.MORNING),
            form_class=TransportPatternForm,
            is_record=False,
            day_value=day_value
        ),
        'return_transport_form': _build_transport_form(
            customer,
            TransportTypeEnum.RETURN,
            prefix=_transport_day_prefix(day_value, TransportTypeEnum.RETURN),
            form_class=TransportPatternForm,
            is_record=False,
            day_value=day_value
        ),
    }

def _build_work_status(
    *,
    owner,              # customer or staff の instance
    day_value,
    pattern_model,      # WorkStatusPatternModel
    owner_field,        # 'customer' or 'staff'
    form_class
):
    if owner.pk:
        instance = pattern_model.objects.filter(
            **{owner_field: owner, 'weekday': day_value}
        ).first()
    else:
        instance = None

    return form_class(
        instance=instance,
        prefix=_day_prefix(day_value),
        initial={'weekday': day_value}
    )

def _save_common(
    *,
    request,
    owner_id,
    owner_model,
    owner_form_class,
    work_status_form_class,
    work_status_model,
    session_form_class,
    session_model,
    owner_field,
    list_redirect_name,
    extra_save=None,
):
    assert request.method == 'POST'

    action = request.POST.get('action')

    if action != 'save':
        return redirect(list_redirect_name)

    # ---- owner 保存 ----
    if owner_id == 0:
        owner = None
        form = owner_form_class(request.POST)
    else:
        owner = owner_model.objects.filter(pk=owner_id).first()
        form = owner_form_class(request.POST, instance=owner)

    if not form.is_valid():
        # エラー時は元のページに飛ばした方が本当はいい
        # if customer_id == 0: #新規作成
        #     customer = None
        #     customer_form = CustomerForm(request.POST) 
        #     template_name = 'customer_create'
        # else:
        #     customer = CustomerModel.objects.filter(pk=customer_id).first()
        #     customer_form = CustomerForm(request.POST, instance=customer) 
        #     template_name = 'edit_customer'    

        # if not customer_form.is_valid():
        #     return render(
        #         request,
        #         template_name,
        #         {'form': customer_form, 'customer_id': customer_id}
        #     )
        return redirect(list_redirect_name)

    with transaction.atomic():
        owner = form.save()

        for day in WeekdayEnum:
            # ---- 勤務ステータス ----
            ws_form = work_status_form_class(
                request.POST,
                prefix=_day_prefix(day.value)
            )

            if ws_form.is_valid():
                ws_cd = ws_form.cleaned_data
                work_status_model.objects.update_or_create(
                    **{
                        owner_field: owner,
                        'weekday': day.value,
                    },
                    defaults={
                        'work_status': ws_cd['work_status']
                    }
                )

            # ---- 勤務セッション ----
            for i in range(WORK_SESSION_COUNT):
                session_form = session_form_class(
                    request.POST,
                    prefix=_session_prefix(day.value, i)
                )

                if not session_form.is_valid():
                    continue

                sf_cd = session_form.cleaned_data

                session_model.objects.update_or_create(
                    **{
                        owner_field: owner,
                        'weekday': day.value,
                        'session_no': i + 1,
                    },
                    defaults={
                        'place': sf_cd['place'],
                        'start_time': sf_cd['start_time'],
                        'end_time': sf_cd['end_time'],
                    }
                )
            # ---------- customer 固有処理 ----------
            if extra_save:
                extra_save(
                    request=request,
                    owner=owner,
                    day_value=day.value
                )

    return redirect(list_redirect_name)

def _customer_extra_save(*, request, owner, day_value):
    # 朝
    _save_transport_pattern(
        request,
        customer=owner,
        day_value=day_value,
        transport_type=TransportTypeEnum.MORNING,
    )

    # 帰り
    _save_transport_pattern(
        request,
        customer=owner,
        day_value=day_value,
        transport_type=TransportTypeEnum.RETURN,
    )    

def staff_save(request, staff_id):
    return _save_common(
        request=request,
        owner_id=staff_id,
        owner_model=StaffModel,
        owner_form_class=StaffForm,
        work_status_form_class=StaffWorkStatusPatternForm,
        work_status_model=StaffWorkStatusPatternModel,
        session_form_class=StaffSessionPatternForm,
        session_model=StaffSessionPatternModel,
        owner_field='staff',
        list_redirect_name='staff_list',
    )

def customer_list_dispatch(request):
    return _list_dispatch(request, kind='customer')

def customer_list(request):
    customers = CustomerModel.objects.all().order_by('order')
    return render(request, 'app/customer_list.html', { 'customers':customers, })

def customer_create(request):
    return _create_or_edit_customer(request)

def customer_edit(request, customer_id):
    return _create_or_edit_customer(request, customer_id)

def _create_or_edit_customer(request, customer_id=None):
    return _create_or_edit_common(
        request=request,
        owner_id=customer_id,
        owner_model=CustomerModel,
        owner_form_class=CustomerForm,
        build_patterns_kwargs=dict(
            work_status_pattern_model=CustomerWorkStatusPatternModel,
            work_status_pattern_form=CustomerWorkStatusPatternForm,
            session_pattern_model=CustomerSessionPatternModel,
            session_form_class=CustomerSessionPatternForm,
            owner_field='customer',
            extra_builder=_build_customer_extra,
        ),
        save_url_name='customer_save',
        id_kwarg_name='customer_id',
        template_name='app/customer_edit.html',
        context_name='customer_form',
    )
    
def _day_prefix(day_value):
    return f'day{day_value}'

def _session_index_prefix(index):
    return f'session{index+1}'

def _session_prefix(day_value, index):
    return f'{_day_prefix(day_value)}_{_session_index_prefix(index)}'

def _transport_prefix(transport_type):
    if transport_type == TransportTypeEnum.MORNING:
        return 'morning'
    else:
        return 'return'

def _transport_day_prefix(day_value, transport_type):
    return f'{_day_prefix(day_value)}_{_transport_prefix(transport_type)}'

def _build_transport_form(obj, transport_type, prefix, form_class, *, is_record=False, day_value=None):

    instance = None

    if obj:
        if is_record:
            instance = TransportRecordModel.objects.filter(
                record=obj,
                transport_type=transport_type
            ).first()
        else:
            if obj.pk is not None:
                instance = TransportPatternModel.objects.filter(
                    customer=obj,
                    weekday=day_value,
                    transport_type=transport_type
                ).first()

    return form_class(
        instance=instance,
        transport_type=transport_type,
        prefix=prefix
    )

def customer_save(request, customer_id):
    return _save_common(
        request=request,
        owner_id=customer_id,
        owner_model=CustomerModel,
        owner_form_class=CustomerForm,
        work_status_form_class=CustomerWorkStatusPatternForm,
        work_status_model=CustomerWorkStatusPatternModel,
        session_form_class=CustomerSessionPatternForm,
        session_model=CustomerSessionPatternModel,
        owner_field='customer',
        list_redirect_name='customer_list',
        extra_save=_customer_extra_save,
    )

def _save_transport_pattern(request, customer, day_value, transport_type):

    form = TransportPatternForm(
        request.POST,
        transport_type=transport_type,
        prefix=_transport_day_prefix(day_value, transport_type)
    )

    if not form.is_valid():
        print(form.errors)
        return False

    cd = form.cleaned_data

    TransportPatternModel.objects.update_or_create(
        customer=customer,
        weekday=day_value,
        transport_type=transport_type,
        defaults={
            'transport_means': cd['transport_means'],
            'place': cd['place'],
            'staff': cd['staff'],
            'time': cd['time'],
        }
    )

    return True

def export(request):

    today = datetime.now().date()
    first_day_of_last_month = (today.replace(day=1) - relativedelta(months=1))
    start_date = CalendarForm(initial_date=first_day_of_last_month)
    end_date = CalendarForm(initial_date=today)

    form = OutputForm()

    return render(request,'app/export.html', {
        'start_date':start_date,
        'end_date':end_date,
        'form':form
        })

def export_execute(request):
    form = OutputForm(request.POST)

    dates = request.POST.getlist('date')
    start_date = dates[0]
    end_date = dates[1]

    if form.is_valid():
        target = form.cleaned_data['target']

        if target == 'customer':
            return exportCustomerWorkData(start_date, end_date)
        elif target == 'staff':
            return exportStaffWorkData(start_date, end_date)

def exportCustomerWorkData(start_date, end_date):

    queryset = CustomerRecordModel.objects.filter(work_date__range=[start_date, end_date]).order_by('customer_id', 'work_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customer_work_data.csv"'

    response.write('\ufeff')

    writer = csv.writer(response)

    writer.writerow([
        '利用者名', '日付', '勤務種別', 
        '送迎(朝)', '送迎場所(朝)', '送迎スタッフ(朝)', '送迎時間(朝)', 
        '送迎(帰り)', '送迎場所(帰り)', '送迎スタッフ(帰り)', '送迎時間(帰り)',
        '昼食', 
        '勤務1(開始時間)','勤務1(終了時間)','勤務1(場所)'
        '勤務2(開始時間)','勤務2(終了時間)','勤務2(場所)'
        '勤務3(開始時間)','勤務3(終了時間)','勤務3(場所)'
    ])

    for record in queryset:
        writer.writerow([
            record.customer.name,
            record.work_date,
            record.get_work_status_display(), 
            record.get_morning_transport_display(), 
            record.pickup_place,
            record.pickup_staff.name if record.pickup_staff else '',
            record.pickup_time.strftime('%H:%M') if record.pickup_time else '',
            record.get_return_transport_display(),
            record.dropoff_place,
            record.dropoff_staff.name if record.dropoff_staff else '',  
            record.dropoff_time.strftime('%H:%M') if record.dropoff_time else '',
            record.work1_start_time.strftime('%H:%M') if record.work1_start_time else '',
            record.work1_end_time.strftime('%H:%M') if record.work1_end_time else '',
            record.work1_place,
            record.work2_start_time.strftime('%H:%M') if record.work2_start_time else '',
            record.work2_end_time.strftime('%H:%M') if record.work2_end_time else '',
            record.work2_place,
            record.work3_start_time.strftime('%H:%M') if record.work3_start_time else '',
            record.work3_end_time.strftime('%H:%M') if record.work3_end_time else '',
            record.work3_place,
        ])

    return response


def exportStaffWorkData(start_date, end_date):
    queryset = StaffRecordModel.objects.filter(work_date__range=[start_date, end_date]).order_by('staff_id', 'work_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="staff_work_data.csv"'

    response.write('\ufeff')

    writer = csv.writer(response)

    writer.writerow([
        'スタッフ名', '日付', '勤務種別',  
        '勤務1(開始時間)','勤務1(終了時間)','勤務1(場所)'
        '勤務2(開始時間)','勤務2(終了時間)','勤務2(場所)'
        '勤務3(開始時間)','勤務3(終了時間)','勤務3(場所)'
    ])

    for record in queryset:
        writer.writerow([
            record.staff.name,
            record.work_date,
            record.get_work_status_text(), 
            record.work1_start_time.strftime('%H:%M') if record.work1_start_time else '',
            record.work1_end_time.strftime('%H:%M') if record.work1_end_time else '',
            record.work1_place,
            record.work2_start_time.strftime('%H:%M') if record.work2_start_time else '',
            record.work2_end_time.strftime('%H:%M') if record.work2_end_time else '',
            record.work2_place,
            record.work3_start_time.strftime('%H:%M') if record.work3_start_time else '',
            record.work3_end_time.strftime('%H:%M') if record.work3_end_time else '',
            record.work3_place,
        ])

    return response

def password_change(request):
    user = request.user  # ログイン中のユーザーを取得
    if request.method == 'POST':
        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # セッションを更新してログアウトを防ぐ
            return redirect('password_change_done')
    else:
        form = PasswordChangeForm(user)
    return render(request, 'app/password_change.html', {'form': form})

def history(request):
    return render(request, 'app/history.html')

MOVE_UP_FUNCS = {
    'staff': lambda pk: _move_order_up(StaffModel, pk),
    'customer': lambda pk: _move_order_up(CustomerModel, pk),
}

MOVE_DOWN_FUNCS = {
    'staff': lambda pk: _move_order_down(StaffModel, pk),
    'customer': lambda pk: _move_order_down(CustomerModel, pk),
}

# def _create_work_sessions_from_pattern2(staff_record):
#     patterns = StaffSessionPatternModel.objects.filter(
#         staff=staff_record.staff,
#         weekday=_get_day(staff_record.work_date)
#     )

#     if not patterns.exists():
#         # パターンがない場合は何もしない
#         return

#     with transaction.atomic():
#         for ptn in patterns:
#             StaffSessionRecordModel.objects.update_or_create(
#                 record=staff_record,
#                 session_no=ptn.session_no,
#                 defaults={
#                     'place': ptn.place,
#                     'start_time': ptn.start_time,
#                     'end_time': ptn.end_time
#                 }
#             )

# def create_customer_work_by_pattern(customer_id, work_date, work_status=None):
 
#     customer = get_object_or_404(CustomerModel, pk=customer_id)

#     with transaction.atomic():

#         rcd, created = CustomerRecordModel.objects.update_or_create(
#             customer=customer,
#             work_date=work_date,
#             defaults={
#                 'work_status': _resolve_work_status(customer, work_date),
#             }
#         )

#         # 通所の場合のみ
#         if rcd.work_status == CustomerWorkStatusEnum.OFFICE:
#             # 勤務セッションを作成
#             _create_work_sessions_from_pattern_common(
#                 record=rcd,
#                 owner_field='customer',
#                 pattern_model=CustomerSessionPatternModel,
#                 session_record_model=CustomerSessionRecordModel
#             )

#             # 送迎を作成
#             _create_transports_from_pattern(
#                 rcd,
#                 TransportTypeEnum.MORNING
#                 )
#             _create_transports_from_pattern(
#                 rcd,
#                 TransportTypeEnum.RETURN
#                 )

#     return rcd
# def _create_work_sessions_from_pattern(customer_record):
#     patterns = CustomerSessionPatternModel.objects.filter(
#         customer=customer_record.customer,
#         weekday=_get_day(customer_record.work_date)
#     )

#     if not patterns.exists():
#         # パターンがない場合は何もしない
#         return

#     with transaction.atomic():
#         for ptn in patterns:
#             CustomerSessionRecordModel.objects.update_or_create(
#                 record=customer_record,
#                 session_no=ptn.session_no,
#                 defaults={
#                     'place': ptn.place,
#                     'start_time': ptn.start_time,
#                     'end_time': ptn.end_time
#                 }
#             )

# def create_info_by_staff(work_date):

#     staffs = StaffModel.objects.all().order_by('order')
#     customer_records = CustomerRecordModel.objects.filter(work_date=work_date).order_by('customer__order')
    
#     info_by_staff = []

#     for staff in staffs:
#         staff_work = StaffRecordModel.objects.filter(staff_id=staff.pk, work_date=work_date).first()
            
#         if not staff_work:
#             staff_work = StaffRecordModel(staff=staff, work_date=work_date)
#             staff_work.staff_name = staff.name

#         places_and_times = []
#         pickup_list = []
#         dropoff_list = []

#         if staff_work.work_status == StaffWorkStatusEnum.ON.value:

#             # 勤務地&勤務時間のリスト
#             for i in range(1,5):
#                 place = getattr(staff_work, f'work{i}_place', None)
#                 start_time = getattr(staff_work, f'work{i}_start_time', None)
#                 end_time = getattr(staff_work, f'work{i}_end_time', None)
#                 if place:
#                     time = f"{start_time.strftime('%H:%M')}～{end_time.strftime('%H:%M')}" if start_time and end_time else ""
#                     places_and_times.append({
#                         'place': place.name,
#                         'time': time
#                     })

#             # 朝の送迎リスト
#             pickup_customers = [customer_record for customer_record in customer_records if customer_record.pickup_staff == staff_work.staff]
            
#             for customer in pickup_customers:
#                 place_info = f"{customer.pickup_place}" if customer.pickup_place else ""
#                 time_info = f"{customer.pickup_time.strftime('%H:%M')}" if customer.pickup_time else ""
#                 car_info = f"{customer.pickup_car}" if customer.pickup_car else ""

#                 pickup_list.append({
#                     'name':customer.customer.name,
#                     'place': place_info,
#                     'time': time_info,
#                     'car': car_info,
#                 })
                        
#             # 帰りの送迎リスト
#             dropoff_customers = [customer_record for customer_record in customer_records if customer_record.dropoff_staff == staff_work.staff]
            
#             for customer in dropoff_customers:
#                 place_info = f"{customer.dropoff_place}" if customer.dropoff_place else ""
#                 time_info = f"{customer.dropoff_time.strftime('%H:%M')}" if customer.dropoff_time else ""
#                 car_info = f"{customer.dropoff_car}" if customer.dropoff_car else ""

#                 dropoff_list.append({
#                     'name':customer.customer.name,
#                     'place': place_info,
#                     'time': time_info,
#                     'car': car_info,
#                 })

        
#         info_by_staff.append({
#             'id':staff_work.staff.pk,
#             'name':staff_work.staff_name,
#             'status':staff_work.get_work_status_text(),
#             'places_and_times':places_and_times,
#             'pickup_list':pickup_list,
#             'dropoff_list':dropoff_list,
#         })
            
#     return info_by_staff

# def config_work(request, work_date):

#     work_date_obj = datetime.strptime(work_date, '%Y-%m-%d').date()
#     calendar_form = CalendarForm(initial_date=work_date_obj)

#     staff_works = StaffRecordModel.objects.filter(work_date=work_date).order_by('staff__order')

#     staff_list = []

#     for staff_work in staff_works:
#         staff_list.append({
#             'id':staff_work.staff.pk,
#             'name': staff_work.staff.name,
#             'work_status': staff_work.get_work_status_display(),
#             'places': [
#                 getattr(staff_work, f'work{i}_place') for i in range(1, WORK_SESSION_COUNT + 1)
#                 if getattr(staff_work, f'work{i}_place') 
#             ],
#         })

#     customer_records = CustomerRecordModel.objects.filter(work_date=work_date).order_by('customer__order')

#     customer_list = []

#     for rcd in customer_records:
#         customer_list.append({
#             'id':rcd.customer.pk,
#             'name': rcd.customer.name,
#             'work_status': rcd.get_work_status_display(),
#             'places': [
#                 getattr(rcd, f'work{i}_place') for i in range(1, WORK_SESSION_COUNT + 1)
#                 if getattr(rcd, f'work{i}_place') 
#             ],
#         })

#     # StaffModelに存在し、StaffWorkModelに存在しないスタッフを取得
#     staffs_with_work_entry = StaffRecordModel.objects.filter(work_date=work_date).values_list('staff', flat=True)
#     staffs_without_work_entry = StaffModel.objects.exclude(id__in=staffs_with_work_entry).order_by('order')

#     # CustomerModelに存在し、CustomerWorkModelに存在しないスタッフを取得
#     customers_with_work_entry = CustomerRecordModel.objects.filter(work_date=work_date).values_list('customer', flat=True)
#     customers_without_work_entry = CustomerModel.objects.exclude(id__in=customers_with_work_entry).order_by('order')
    
#     return render(request,'app/config_work.html',{
#         'calendar_form':calendar_form,
#         'work_date':work_date,
#         'staff_list':staff_list,
#         'customer_list':customer_list,
#         'staffs_without_work_entry':staffs_without_work_entry,
#         'customers_without_work_entry':customers_without_work_entry,
#         })

# def _resolve_work_status(customer, work_date):

#     pattern = CustomerWorkStatusPatternModel.objects.filter(
#         customer = customer,
#         weekday = _get_day(work_date)
#     ).first()

#     if pattern:
#         return pattern.work_status

#     return CustomerWorkStatusEnum.OFF

# def _resolve_work_status2(staff, work_date):
#     pattern = StaffWorkStatusPatternModel.objects.filter(
#         staff = staff,
#         weekday = _get_day(work_date)
#     ).first()

#     if pattern:
#         return pattern.work_status

#     return StaffWorkStatusEnum.OFF

# def _create_customer_record_from_pattern(customer, work_date):

#     with transaction.atomic():
#         work_status = _resolve_work_status_common(
#             owner=customer,
#             work_date=work_date,
#             pattern_model=CustomerWorkStatusPatternModel,
#             owner_field='customer',
#             off_value=CustomerWorkStatusEnum.OFF,
#         )
#         rcd, created = CustomerRecordModel.objects.update_or_create(
#             customer=customer,
#             work_date=work_date,
#             defaults={
#                 'work_status': work_status,
#             }
#         )    

#         # 勤務セッションを作成
#         _create_work_sessions_from_pattern_common(
#             record=rcd,
#             owner_field='customer',
#             pattern_model=CustomerSessionPatternModel,
#             session_record_model=CustomerSessionRecordModel
#         )

#         # 送迎を作成
#         _create_transports_from_pattern(rcd, TransportTypeEnum.MORNING)
#         _create_transports_from_pattern(rcd, TransportTypeEnum.RETURN) 

# def _create_staff_record_from_pattern(staff, work_date):
#     with transaction.atomic():
#         work_status = _resolve_work_status_common(
#             owner=staff,
#             work_date=work_date,
#             pattern_model=StaffWorkStatusPatternModel,
#             owner_field='staff',
#             off_value=StaffWorkStatusEnum.OFF,
#         )
#         rcd, created = StaffRecordModel.objects.update_or_create(
#             staff=staff,
#             work_date=work_date,
#             defaults={
#                 'work_status': work_status,
#             }
#         )    

#         # 勤務セッションを作成
#         _create_work_sessions_from_pattern_common(
#             record=rcd,
#             owner_field='staff',
#             pattern_model=StaffSessionPatternModel,
#             session_record_model=StaffSessionRecordModel,
#         )

# def create_staff_work_by_pattern(staff_id, work_date, work_status=None):
 
#     staff = get_object_or_404(StaffModel, pk=staff_id)
#     staff_work = StaffRecordModel(staff=staff, work_date=work_date)

#     if work_status == StaffWorkStatusEnum.ON:
#         staff_work.work_status = work_status
#     else:
#         # 曜日ごとのステータスを設定
#         weekday_number = datetime.strptime(work_date, "%Y-%m-%d").date().weekday()
#         if weekday_number == 0:
#             staff_work.work_status = staff.work_status_mon
#         elif weekday_number == 1:
#             staff_work.work_status = staff.work_status_tue
#         elif weekday_number == 2:
#             staff_work.work_status = staff.work_status_wed        
#         elif weekday_number == 3:
#             staff_work.work_status = staff.work_status_thu
#         elif weekday_number == 4:
#             staff_work.work_status = staff.work_status_fri        
#         elif weekday_number == 5:
#             staff_work.work_status = staff.work_status_sat   
#         elif weekday_number == 6:
#             staff_work.work_status = staff.work_status_sun

#     # ステータスが「OFFICE」の場合に詳細を設定
#     if staff_work.work_status == StaffWorkStatusEnum.ON:
#         staff_work.work1_start_time = staff.work1_start_time
#         staff_work.work1_end_time = staff.work1_end_time
#         staff_work.work1_place = staff.work1_place
#         staff_work.work2_start_time = staff.work2_start_time
#         staff_work.work2_end_time = staff.work2_end_time
#         staff_work.work2_place = staff.work2_place
#         staff_work.work3_start_time = staff.work3_start_time
#         staff_work.work3_end_time = staff.work3_end_time
#         staff_work.work3_place = staff.work3_place
#         staff_work.work4_start_time = staff.work4_start_time
#         staff_work.work4_end_time = staff.work4_end_time
#         staff_work.work4_place = staff.work4_place

#     return staff_work