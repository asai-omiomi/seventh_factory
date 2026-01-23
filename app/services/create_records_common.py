from django.db import transaction
from app.models import StaffModel, CustomerModel, StaffRecordModel, CustomerRecordModel, TransportRecordModel, StaffPatternModel, CustomerPatternModel, StaffSessionPatternModel, CustomerSessionPatternModel, StaffSessionRecordModel, CustomerSessionRecordModel, TransportPatternModel, StaffWorkStatusEnum, CustomerWorkStatusEnum, TransportTypeEnum
import datetime
from django.utils import timezone
import jpholiday

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
        TransportRecordModel.objects.update_or_create(
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

def _get_day(work_date):
    if isinstance(work_date, str):
        work_date = datetime.datetime.strptime(work_date, "%Y-%m-%d").date()
    return work_date.weekday() + 1

def _get_pattern_record(
    *,
    member,
    work_date,
    pattern_model,
    member_field,
):
    pattern = pattern_model.objects.filter(
        **{
            member_field: member,
            'weekday': _get_day(work_date),
        }
    ).first()

    return pattern

def _create_record_from_pattern_common(
    *,
    user_name,
    member,
    work_date,
    record_model,
    member_field,
    work_status_pattern_model,
    off_value,
    session_pattern_model,
    session_record_model,
    with_transport=False,
):
    with transaction.atomic():
        # 勤務ステータス解決
        prcd = _get_pattern_record(
            member=member,
            work_date=work_date,
            pattern_model=work_status_pattern_model,
            member_field=member_field,
        )

        # レコード作成 or 更新
        rcd, _ = record_model.objects.update_or_create(
            **{
                member_field: member,
                'work_date': work_date,
            },
            defaults={
                'work_status': prcd.work_status if prcd else off_value,
                'remarks': prcd.remarks if prcd else ""
            }
        )

        # 変更履歴
        save_change_history(
            user_name=user_name,
            record = rcd, 
            content_text="新規作成"
            )

        # 勤務セッション作成
        _create_work_sessions_from_pattern_common(
            record=rcd,
            member_field=member_field,
            pattern_model=session_pattern_model,
            session_record_model=session_record_model,
        )

        # 送迎（必要な場合のみ）
        if with_transport:
            _create_transports_from_pattern(rcd, TransportTypeEnum.MORNING)
            _create_transports_from_pattern(rcd, TransportTypeEnum.RETURN)

    return rcd

def save_change_history(
        user_name, 
        *, 
        record, 
        content_text): 
    
    now = timezone.localtime().strftime("%m/%d %H:%M:%S")

    history_text = (
        f'[{now}]{content_text} by{user_name}\n'
    )

    record.change_history = history_text + record.change_history
    record.save()

def _create_work_sessions_from_pattern_common(
    *,
    record,
    member_field,
    pattern_model,
    session_record_model,
):
    member = getattr(record, member_field)

    patterns = pattern_model.objects.filter(
        **{
            member_field: member,
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

def _create_records_from_pattern_common(
    *,
    user_name,
    work_date,
    member_model,
    record_model,
    member_field,
    work_status_pattern_model,
    off_value,
    session_pattern_model,
    session_record_model,
    with_transport=False,
    order_field='order',
):
    owners = member_model.objects.all().order_by(order_field)

    for member in owners:
        _create_record_from_pattern_common(
            user_name=user_name,
            member=member,
            work_date=work_date,
            record_model=record_model,
            member_field=member_field,
            work_status_pattern_model=work_status_pattern_model,
            off_value=off_value,
            session_pattern_model=session_pattern_model,
            session_record_model=session_record_model,
            with_transport=with_transport,
        )

def create_records(user_name, work_date):

    is_holiday = jpholiday.is_holiday(work_date)

    if is_holiday:
        create_records_off_day(user_name, work_date)
    else:
        create_records_by_pattern(user_name, work_date)
        

def create_records_by_pattern(user_name, work_date):
    # staff
    _create_records_from_pattern_common(
        user_name=user_name,
        work_date=work_date,
        member_model=StaffModel,
        record_model=StaffRecordModel,
        member_field='staff',
        work_status_pattern_model=StaffPatternModel,
        off_value=StaffWorkStatusEnum.OFF,
        session_pattern_model=StaffSessionPatternModel,
        session_record_model=StaffSessionRecordModel,
        with_transport=False,
    )

    # customer
    _create_records_from_pattern_common(
        user_name=user_name,
        work_date=work_date,
        member_model=CustomerModel,
        record_model=CustomerRecordModel,
        member_field='customer',
        work_status_pattern_model=CustomerPatternModel,
        off_value=CustomerWorkStatusEnum.OFF,
        session_pattern_model=CustomerSessionPatternModel,
        session_record_model=CustomerSessionRecordModel,
        with_transport=True,
    )

def create_records_off_day(user_name, work_date):
    with transaction.atomic():  # まとめてトランザクション
        # --- Staff ---
        for staff in StaffModel.objects.all():
            rcd, created = StaffRecordModel.objects.get_or_create(
                staff=staff,
                work_date=work_date,
                defaults={
                    'work_status': StaffWorkStatusEnum.OFF,
                }
            )

            if created:
                save_change_history(
                    user_name=user_name,
                    record=rcd,
                    content_text="新規作成"
                )          

        # --- Customer ---
        for customer in CustomerModel.objects.all():
            rcd, created = CustomerRecordModel.objects.get_or_create(
                customer=customer,
                work_date=work_date,
                defaults={
                    'work_status': CustomerWorkStatusEnum.OFF,
                }
            )

            if created:
                save_change_history(
                    user_name=user_name,
                    record=rcd,
                    content_text="新規作成"
                )    