from django.shortcuts import render, redirect,get_object_or_404
from django.views.generic.base import TemplateView
from .models import CustomerModel,CustomerRecordModel,StaffModel,CustomerWorkStatusPatternModel,StaffRecordModel, StaffSessionRecordModel,StaffWorkStatusPatternModel,CustomerSessionRecordModel,CustomerSessionPatternModel,TransportPatternModel,StaffSessionPatternModel,TransportRecordModel,WeekdayEnum, PlaceModel, PlaceRemarksModel, OperationLogModel, TransportMeansEnum,TransportTypeEnum,StaffWorkStatusEnum, CustomerWorkStatusEnum, CurrentStatusStaffEnum,CurrentStatusCustomerEnum, WORK_SESSION_COUNT
from .forms import CustomerWorkStatusPatternForm,PlaceRemarksForm,StaffForm,StaffRecordForm,CustomerForm,CustomerWorkStatusPatternForm,CustomerSessionPatternForm,CustomerSessionRecordForm,StaffSessionRecordForm,TransportPatternForm,TransportRecordForm,StaffSessionPatternForm,CustomerRecordForm,StaffWorkStatusPatternForm,CalendarForm,OutputForm
import datetime
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse
from django.urls import reverse
import csv
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from django.forms.models import model_to_dict
from django.db import models
from django.utils import timezone
from django.contrib import messages

class IndexView(TemplateView):
    template_name = 'app/index.html'

def info_today(request):
    return redirect('info', timezone.now().date())

def info(request, work_date):
    # =========================
    # POST：勤務状態の更新
    # =========================
    if request.method == "POST" and "edit_current_status" in request.POST:
        _update_session_current_status(
            request,
            member_type=request.POST["member_type"],
            member_id=int(request.POST["member_id"]),
            work_date=request.POST["work_date"],
            place_id=int(request.POST["place_id"]),
            new_status=int(request.POST["current_status"]),
        )

        return redirect("info", work_date=request.POST["work_date"])
    # =========================
    # GET：通常の表示
    # =========================
    calendar_form = CalendarForm(initial_date=work_date)

    # 全体情報
    info = _build_info(work_date)

    # 送迎情報
    transport_table_rows = _build_transport_table_rows(work_date)

    return render(request,'app/info.html',{
        'work_date':work_date,
        'calendar_form':calendar_form,
        'info': info,
        'transport_table_rows': transport_table_rows, 
        'current_status_staff_choices': CurrentStatusStaffEnum.choices,
        'current_status_customer_choices': CurrentStatusCustomerEnum.choices,
        })

def _update_session_current_status(
    request,
    *,
    member_type,
    member_id,
    work_date,
    place_id,
    new_status,
):
    if member_type == "staff":
        record = StaffRecordModel.objects.get(
            staff_id=member_id,
            work_date=work_date,
        )
        member_name = record.staff.name
        session_model = StaffSessionRecordModel
        special_statuses = [CurrentStatusStaffEnum.ABSENT]
        record_status_mapping = {
            CurrentStatusStaffEnum.ABSENT: StaffWorkStatusEnum.OFF
        }
        initial_status = CurrentStatusStaffEnum.BEFORE

    elif member_type == "customer":
        record = CustomerRecordModel.objects.get(
            customer_id=member_id,
            work_date=work_date,
        )
        member_name = record.customer.name
        session_model = CustomerSessionRecordModel
        special_statuses = [CurrentStatusCustomerEnum.HOME, CurrentStatusCustomerEnum.ABSENT]
        record_status_mapping = {
            CurrentStatusCustomerEnum.HOME: CustomerWorkStatusEnum.HOME,
            CurrentStatusCustomerEnum.ABSENT: CustomerWorkStatusEnum.OFF
        }
        initial_status = CurrentStatusCustomerEnum.BEFORE

    else:
        raise ValueError("invalid member_type")

    if new_status not in special_statuses:
        # 通常の更新：current_status のみ
        sessions = session_model.objects.filter(
            record=record,
            place_id=place_id,
        )

        for session in sessions:
            # prev_status = session.current_status
            session.current_status = new_status
            session.save()
            
            # log_operation(
            #     user=request.user,
            #     action='UPDATE',
            #     target=session,
            #     description=(
            #         f'[{work_date}][{member_name}]'
            #         f'[{session.place.name}][勤務ステータス変更]'
            #         f'【{prev_status}→{new_status}】'
            #     ),
            # )     

    else:
        # 在宅・休みの場合:全セッションを初期化
        sessions = session_model.objects.filter(
            record=record,
        )

        sessions.update(
            current_status=initial_status,
            place=None,
            start_time=None,
            end_time=None
        )

        # recordModel の work_status を更新
        record.work_status = record_status_mapping[new_status]
        record.save()
       

def _build_info(work_date):

    staff_records = StaffRecordModel.objects.filter(work_date=work_date).order_by('staff__order')

    customer_records = CustomerRecordModel.objects.filter(work_date=work_date).order_by('customer__order')

    if not staff_records and not customer_records:
        return []

    info = []

    # 勤務地別を追加
    _append_place_info(staff_records, customer_records, work_date, info)
    # 勤務地なしを追加
    _append_no_place_info(staff_records, customer_records, info)
    # 在宅を追加
    _append_home_info(customer_records, info)
    # 休みを追加
    _append_off_info(staff_records, customer_records, info)

    return info

def _append_place_info(staff_records, customer_records, work_date, info):
    places = PlaceModel.objects.all()

    for place in places:
        staff_list = _build_member_list_by_place(
            staff_records,
            place=place,
            get_member=lambda rcd: rcd.staff,
            session_model=StaffSessionRecordModel,
        )
        customer_list = _build_member_list_by_place(
            customer_records,
            place=place,
            get_member=lambda rcd: rcd.customer,
            session_model=CustomerSessionRecordModel,
            extra_lines_builder=_build_customer_extra_lines,
        ) 
        staff_customer_list = _build_staff_customer_list(staff_list, customer_list)
        remarks = _build_remarks(place, work_date)

        info.append({
            'place_id': place.id,
            'place_name': place.name,
            'color': "table-secondary",
            'staff_cusotmer_list': staff_customer_list,
            'remarks': remarks,
        })  

def has_any_place_session(rcd, session_model):
    """
    1つでも place が設定されたセッションがあるか
    """
    return session_model.objects.filter(
        record=rcd,
        place__isnull=False,
    ).exists()

def _build_member_list_without_place(
    records,
    *,
    get_member,
    session_model,
    work_status,
):
    result = []

    for rcd in records:
        member = get_member(rcd)
        if not member:
            continue

        # 出勤/通所だけれども場所が1つも設定されていない
        if rcd.work_status == work_status:
            if not has_any_place_session(rcd, session_model):
                result.append({
                    'id': member.id,
                    'name': member.name,
                    'display': "",
                    'change_history':rcd.change_history,
                })

    return result

def _append_no_place_info(
    staff_records,
    customer_records,
    info,
):
    staff_list = _build_member_list_without_place(
        staff_records,
        get_member=lambda rcd: rcd.staff,
        session_model=StaffSessionRecordModel,
        work_status=StaffWorkStatusEnum.ON,
    )

    customer_list = _build_member_list_without_place(
        customer_records,
        get_member=lambda rcd: rcd.customer,
        session_model=CustomerSessionRecordModel,
        work_status=CustomerWorkStatusEnum.OFFICE,
    )

    if not staff_list and not customer_list:
        return  # 空なら追加しない

    staff_customer_list = _build_staff_customer_list(
        staff_list,
        customer_list
    )

    info.append({
        'place_id': -1,
        'place_name': "場所未設定",
        'color': "table-warning",
        'staff_cusotmer_list': staff_customer_list,
        'remarks': "",
    })   

def _append_home_info(customer_records, info):
    _append_status_info(
            info=info,
            place_id=-2,
            place_name="在宅",
            color="table-success",
            customer_records=customer_records,
            customer_work_status=CustomerWorkStatusEnum.HOME,
        )

def _append_off_info(staff_records, customer_records, info):
    _append_status_info(
        info=info,
        place_id=-3,
        place_name="休み",
        color="table-danger",
        staff_records=staff_records,
        staff_work_status=[
            StaffWorkStatusEnum.OFF,
            StaffWorkStatusEnum.OFF_WITH_PAY,
        ],
        customer_records=customer_records,
        customer_work_status=CustomerWorkStatusEnum.OFF,
    )   

def _append_status_info(
    *,
    info,
    place_id,
    place_name,
    color,
    staff_records=None,
    customer_records=None,
    staff_work_status=None,
    customer_work_status=None,
):
    staff_list = []
    customer_list = []

    if staff_records is not None and staff_work_status is not None:
        staff_list = _build_member_list_by_work_status(
            staff_records,
            get_member=lambda rcd: rcd.staff,
            work_status=staff_work_status,
        )

    if customer_records is not None and customer_work_status is not None:
        customer_list = _build_member_list_by_work_status(
            customer_records,
            get_member=lambda rcd: rcd.customer,
            work_status=customer_work_status,
        )

    staff_customer_list = _build_staff_customer_list(
        staff_list or None,
        customer_list or None,
    )

    info.append({
        'place_id': place_id,
        'place_name': place_name,
        'color': color,
        'staff_cusotmer_list': staff_customer_list,
        'remarks': "",
    })


def _build_member_list_by_work_status(
    records,
    *,
    get_member,
    work_status,
):
    # 複数対応
    if work_status is None:
        work_status_set = None
    elif isinstance(work_status, (list, tuple, set)):
        work_status_set = set(work_status)
    else:
        work_status_set = {work_status}

    result = []

    for rcd in records:
        member = get_member(rcd)
        if not member:
            continue

        if work_status_set is not None and rcd.work_status in work_status_set:
            if hasattr(rcd, 'work_status') and rcd.work_status == StaffWorkStatusEnum.OFF_WITH_PAY:
                display_name = "有給"

            result.append({
                'id': member.id,
                'name': member.name,
                'display': display_name,
                'change_history':rcd.change_history,
            })

    return result

def _build_member_list_by_place(
    records,
    *,
    place,
    get_member,
    session_model,
    extra_lines_builder=None,
):
    result = []

    for rcd in records:
        member = get_member(rcd)
        if not member:
            continue

        sessions = (
            session_model.objects
            .filter(record=rcd, place=place)
            .order_by('session_no')
        )

        if not sessions.exists():
            continue

        lines = []

        for s in sessions:
            if s.start_time and s.end_time:
                lines.append(
                    f"{s.start_time.strftime('%H:%M')}～{s.end_time.strftime('%H:%M')}"
                )

        if extra_lines_builder:
            lines.extend(extra_lines_builder(rcd))

        # current_status は session 側から取る
        first_session = sessions[0]

        result.append({
            'id': member.id,
            'name': member.name,
            'display': "\n".join(lines),
            'current_status': first_session.current_status,
            'current_status_text': first_session.get_current_status_display(),
            'current_status_btn_class': _status_btn_class(first_session.current_status),
            'change_history':rcd.change_history,
        })

    return result

def _status_btn_class(status):
    return {
        CurrentStatusCustomerEnum.BEFORE:   "btn-outline-primary",
        CurrentStatusCustomerEnum.WORKING:  "btn-primary",
        CurrentStatusCustomerEnum.FINISHED: "btn-secondary",
        CurrentStatusCustomerEnum.MOVED:    "btn-secondary",
        CurrentStatusCustomerEnum.HOME:     "btn-success",
        CurrentStatusCustomerEnum.ABSENT:   "btn-danger",

        # スタッフは↑の中にすべて入っているので、別で定義しなくてよい

    }.get(status, "btn-outline-secondary")

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
            if transport.remarks:
                text += f" {transport.remarks}"

        lines.append(text)

    return lines
    
def _build_remarks(place=None, work_date=None):
    if not place:
        return ""

    place_remarks = PlaceRemarksModel.objects.filter(place=place, work_date=work_date).first()
    if place_remarks:
        return place_remarks.remarks or ""
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
        t.place or '',
        t.remarks,
    ]
    return ' '.join(p for p in parts if p)

def info_dispatch(request, work_date):
    assert request.method == 'POST'

    change_date = request.POST.get('change_date')
    create_records = request.POST.get('create_records')
    place_remarks_edit = request.POST.get('place_remarks_edit')
    customer_record_edit = request.POST.get('customer_record_edit')
    staff_record_edit = request.POST.get('staff_record_edit')
    create_records = request.POST.get('create_records')
    create_records_off_day = request.POST.get('create_records_off_day')
   
    if change_date:
        work_date = request.POST.get('date')
        return redirect('info', work_date)
    elif create_records:
        work_date = request.POST.get('date')
        _create_records(work_date)
        return redirect('info', work_date)
    elif create_records_off_day:
        _create_records_off_day(work_date)
        return redirect('info', work_date)
    elif place_remarks_edit:
        place_id = place_remarks_edit
        return redirect('place_remarks_edit', place_id, work_date)
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

def _create_records_off_day(work_date):
    with transaction.atomic():  # まとめてトランザクション
        # --- Staff ---
        for staff in StaffModel.objects.all():
            record_exists = StaffRecordModel.objects.filter(
                staff=staff,
                work_date=work_date
            ).exists()
            if not record_exists:
                StaffRecordModel.objects.create(
                    staff=staff,
                    work_date=work_date,
                    work_status=StaffWorkStatusEnum.OFF
                )

        # --- Customer ---
        for customer in CustomerModel.objects.all():
            record_exists = CustomerRecordModel.objects.filter(
                customer=customer,
                work_date=work_date
            ).exists()
            if not record_exists:
                CustomerRecordModel.objects.create(
                    customer=customer,
                    work_date=work_date,
                    work_status=CustomerWorkStatusEnum.OFF
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
        work_date = datetime.datetime.strptime(work_date, "%Y-%m-%d").date()
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
                'remarks': pattern.remarks,
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
    return _record_save_common(
        request,
        member_id=staff_id,
        work_date=work_date,
        member_model=StaffModel,
        record_model=StaffRecordModel,
        record_form_class=StaffRecordForm,
        session_form_class=StaffSessionRecordForm,
        session_model=StaffSessionRecordModel,
        member_field='staff',
    )    

#################################################
# 利用者実績画面でボタン(保存/キャンセル)を
# 押したときの処理
################################################
def customer_record_save(request, customer_id, work_date):   
    return _record_save_common(
        request,
        member_id=customer_id,
        work_date=work_date,
        member_model=CustomerModel,
        record_model=CustomerRecordModel,
        record_form_class=CustomerRecordForm,
        session_form_class=CustomerSessionRecordForm,
        session_model=CustomerSessionRecordModel,
        member_field='customer',
        extra_save_func=_customer_record_extra_save,
    )

def _record_save_common(
    request,
    *,
    member_id,
    work_date,
    member_model,
    record_model,
    record_form_class,
    session_form_class,
    session_model,
    member_field,           # 'staff' or 'customer'
    extra_save_func=None,   # 送迎など
):
    assert request.method == 'POST'

    if request.POST.get('action') != 'save':
        return redirect('info', work_date)

    member = get_object_or_404(member_model, pk=member_id)

    # 既存レコードを取得（なければ None）
    record = record_model.objects.filter(
        **{
            member_field: member,
            'work_date': work_date,
        }
    ).first()

    # before = snapshot_for_log(record)
    
    record_form = record_form_class(request.POST)

    if not record_form.is_valid():
        # 通常はここに来ない想定（来るならエラーハンドリング）
        return redirect('info', work_date)        

    # 既存レコードを更新
    for field, value in record_form.cleaned_data.items():
        setattr(record, field, value)
    record.save()

    # after = snapshot_for_log(record)

    # diff = make_diff(before, after, record, MEMBER_RECORD_FIELD_MAP)

    # if diff:            
    #     log_operation(
    #         user=request.user if request else None,
    #         action='CREATE' if before is None else 'UPDATE',
    #         target=record,
    #         description=f'{work_date}の{member.name}の勤務情報を更新',
    #         diff=diff,
    #     )

    # 勤務セッション保存
    for i in range(WORK_SESSION_COUNT):

        session_form = session_form_class(
            request.POST,
            prefix=_session_index_prefix(i)
        )

        if not session_form.is_valid():
            continue

        cd = session_form.cleaned_data
        session_no = i + 1

        # 既存セッション取得
        session = session_model.objects.filter(
            record=record,
            session_no=session_no,
        ).first()

        # before = snapshot_for_log(session)

        session.place = cd['place']
        session.start_time = cd['start_time']
        session.end_time = cd['end_time']
        session.save()

        # after = snapshot_for_log(session)

        # diff = make_diff(before, after, session, SESSION_FIELD_MAP)

        # if diff:
        #     log_operation(
        #         user=request.user,
        #         action='UPDATE',
        #         target=session,
        #         description=(
        #             f'{work_date}の{member.name}の'
        #             f'勤務{session_no}を更新'
        #         ),
        #         diff=diff,
        #     )            

    # 追加保存（送迎など）
    if extra_save_func:
        extra_save_func(request, record)

    return redirect('info', work_date)

def _customer_record_extra_save(request, record):
    _save_transport_record(request, record, TransportTypeEnum.MORNING)
    _save_transport_record(request, record, TransportTypeEnum.RETURN)


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
            'remarks': cd['remarks'],
        }
    )

    return True

def place_remarks_edit(request, place_id, work_date):

    if request.POST.get('action') != 'save':
        return redirect('info', work_date=work_date)

    place = PlaceModel.objects.get(pk=place_id)

    place_remarks, created = PlaceRemarksModel.objects.get_or_create(
        place=place, 
        work_date=work_date,
    )

    form = PlaceRemarksForm(instance=place_remarks)

    return render(
        request, 
        'app/place_remarks_edit.html',
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
        'weekday_choices':WeekdayEnum.choices,
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
            'remarks': cd['remarks'],
        }
    )

    return True

def sysad(request):
    calendar_form = CalendarForm(initial_date=timezone.now().date())

    return render(request,'app/sysad.html', {
            'calendar_form':calendar_form,
        })

def delete_record(request):
    print("0")
    if request.method == 'POST':
        print("1")
        date = request.POST.get('date')

    if not date:
        print("2")
        # 日付が指定されていなければ戻す
        return redirect('sysad')

    # トランザクション内でまとめて削除
    with transaction.atomic():
        # 1. 顧客セッション
        CustomerSessionRecordModel.objects.filter(record__work_date=date).delete()

        # 2. 顧客レコード
        CustomerRecordModel.objects.filter(work_date=date).delete()

        # 3. スタッフセッション
        StaffSessionRecordModel.objects.filter(record__work_date=date).delete()

        # 4. スタッフレコード
        StaffRecordModel.objects.filter(work_date=date).delete()

        # 5. 送迎記録
        TransportRecordModel.objects.filter(record__work_date=date).delete()

        # 6. 場所備考
        PlaceRemarksModel.objects.filter(work_date=date).delete()

        print("成功")
        messages.success(request, f"{date} のデータを削除しました。")

    return redirect('sysad')

def output(request):

    today = timezone.now().date()
    first_day_of_last_month = (today.replace(day=1) - relativedelta(months=1))
    start_date = CalendarForm(initial_date=first_day_of_last_month)
    end_date = CalendarForm(initial_date=today)

    form = OutputForm()

    return render(request,'app/output.html', {
        'start_date':start_date,
        'end_date':end_date,
        'form':form
        })

def output_execute(request):
    form = OutputForm(request.POST)

    date_set = request.POST.getlist('date')
    start_date = date_set[0]
    end_date = date_set[1]

    if not form.is_valid():
        return redirect('output')

    target = form.cleaned_data['target']

    if target == 'customer':
        return _output_member_records(
        start_date=start_date,
        end_date=end_date,
        record_model=CustomerRecordModel,
        member_field='customer',
        session_related_name='customer_session_record',
        filename='customer.csv',
        include_transport=True,
    )
    elif target == 'staff':
        return _output_member_records(
        start_date=start_date,
        end_date=end_date,
        record_model=StaffRecordModel,
        member_field='staff',
        session_related_name='staff_session_record',
        filename='staff.csv',
        include_transport=False,
    )
    else:
        return redirect('output')
    
def _output_member_records(
    *,
    start_date,
    end_date,
    record_model,
    member_field,                 
    session_related_name,         
    filename,
    include_transport=False,
):
    qs = (
        record_model.objects
        .filter(work_date__range=[start_date, end_date])
        .select_related(member_field)
        .prefetch_related(session_related_name)
        .order_by(f'{member_field}__order', 'work_date')
    )

    if include_transport:
        qs = qs.prefetch_related('record_transport')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response)

    # --- ヘッダ ---
    header = [
        '名前', '日付', '勤務種別',
        '勤務1(場所)', '勤務1(開始)', '勤務1(終了)',
        '勤務2(場所)', '勤務2(開始)', '勤務2(終了)',
        '勤務3(場所)', '勤務3(開始)', '勤務3(終了)',
    ]

    if include_transport:
        header.extend([
            '送迎(朝)', '送迎場所(朝)', '送迎スタッフ(朝)', '備考(朝)',
            '送迎(帰り)', '送迎場所(帰り)', '送迎スタッフ(帰り)', '備考(帰り)',
        ])

    writer.writerow(header)

    # --- 本体 ---
    for record in qs:
        row = []

        member = getattr(record, member_field)

        row.append(member.name if member else '')
        row.append(record.work_date)
        row.append(record.get_work_status_display())

        sessions = list(
            getattr(record, session_related_name)
            .all()
            .order_by('session_no')
        )

        for i in range(WORK_SESSION_COUNT):
            if i < len(sessions):
                s = sessions[i]
                row.extend([
                    str(s.place) if s.place else '',
                    s.start_time.strftime('%H:%M') if s.start_time else '',
                    s.end_time.strftime('%H:%M') if s.end_time else '',
                ])
            else:
                row.extend(['', '', ''])

        if include_transport:
            transports = {
                t.transport_type: t
                for t in record.record_transport.all()
            }

            def transport_cols(t):
                return [
                    t.get_transport_means_display(),
                    str(t.place) if t.place else '',
                    str(t.staff) if t.staff else '',
                    t.remarks,
                ]

            row.extend(
                transport_cols(transports.get(TransportTypeEnum.MORNING))
                if TransportTypeEnum.MORNING in transports else
                ['', '', '', '']
            )

            row.extend(
                transport_cols(transports.get(TransportTypeEnum.RETURN))
                if TransportTypeEnum.RETURN in transports else
                ['', '', '', '']
            )

        writer.writerow(row)

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

MEMBER_RECORD_FIELD_MAP = {
    'work_date': '勤務日',
    'work_status': '勤務種別',
}

SESSION_FIELD_MAP = {
    'place': '場所',
    'start_time': '開始時間',
    'start_time': '終了時間',
    'current_status': '勤務ステータス'
}

def model_snapshot(instance):
    """モデルインスタンスを dict に変換"""
    if instance is None:
        return {}
    return model_to_dict(instance)

def snapshot_for_log(instance):
    raw = model_snapshot(instance)
    result = {}

    for field, value in raw.items():
        result[field] = normalize_value(
            value,
            instance=instance,
            field_name=field,
        )

    return result

def make_diff(before, after, instance, field_map):
    diff = {}

    for field, after_value in after.items():
        before_value = before.get(field)

        if before_value == after_value:
            continue

        label = field_map.get(field, field)

        diff[label] = {
            'before': normalize_value(before_value, instance=instance, field_name=field),
            'after':  normalize_value(after_value,  instance=instance, field_name=field),
        }

    return diff

def normalize_value(value, *, instance=None, field_name=None):
    if value is None:
        return None

    # datetime
    if isinstance(value, datetime.datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')

    # date
    if isinstance(value, datetime.date):
        return value.strftime('%Y-%m-%d')

    # time
    if isinstance(value, datetime.time):
        return value.strftime('%H:%M')

    # ForeignKey（モデル）
    if isinstance(value, models.Model):
        return str(value)

    # ChoiceField（IntegerChoicesなど）
    if instance and field_name:
        try:
            field = instance._meta.get_field(field_name)
            if field.choices:
                return dict(field.choices).get(value, value)
        except Exception:
            pass

    # JSONにそのまま出せる型
    if isinstance(value, (int, float, str, bool)):
        return value

    # fallback（最後の砦）
    return str(value)



def log_operation(
    *,
    user=None,
    action,
    target=None,       # モデルインスタンス
    description='',
    diff=None,
):
    if target is not None:
        try:
            target_model = target.__class__.__name__
            target_id = target.pk
        except AttributeError:
            raise ValueError("target には必ずモデルのインスタンスを渡してください")
    else:
        target_model = ''
        target_id = None

    OperationLogModel.objects.create(
        user=user,
        action=action,
        target_model=target_model,
        target_id=target_id,
        description=description,
        diff=diff,
    )