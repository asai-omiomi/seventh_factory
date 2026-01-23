# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

WORK_SESSION_COUNT = 3

class StaffWorkStatusEnum(models.IntegerChoices):
    ON              = 1, "出勤"
    OFF             = 9, "欠勤"
    OFF_WITH_PAY    = 10, "有給"

class CustomerWorkStatusEnum(models.IntegerChoices):
    OFFICE  = 1, "通所"
    HOME    = 8, "在宅"
    OFF     = 9, "休み"

class TransportMeansEnum(models.IntegerChoices):
    TRANSFER    = 1, "送迎"
    CAR         = 2, "車"
    BUS         = 3, "バス"
    BICYCLE     = 4, "自転車"
    WALK        = 5, "徒歩"
    MOTORCYCLE  = 6, "バイク"
    OTHERS      = 9, "その他"

class CurrentStatusEnum(models.IntegerChoices):
    BEFORE   = 0, "出勤前 / 通所前"
    WORKING  = 1, "勤務中"
    FINISHED = 5, "退勤済"
    # HOME     = 8, "在宅"
    # ABSENT   = 9, "休み"

class TransportTypeEnum(models.IntegerChoices):
    MORNING = 1, '朝'
    RETURN  = 2, '帰り'

class WeekdayEnum(models.IntegerChoices):
    MON = 1, '月'
    TUE = 2, '火'
    WED = 3, '水'
    THU = 4, '木'
    FRI = 5, '金'
    SAT = 6, '土'
    SUN = 7, '日'

from django.db import models

class BaseMemberModel(models.Model):
    name = models.CharField(
        max_length=20,
        blank=False,
        default=''
    )

    order = models.IntegerField(
        blank=False,
        null=False,
    )

    class Meta:
        abstract = True
        ordering = ['order']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk:
            max_order = (
                self.__class__
                .objects
                .aggregate(models.Max('order'))
                ['order__max']
            )
            self.order = max_order + 1 if max_order is not None else 1

        super().save(*args, **kwargs)

class StaffModel(BaseMemberModel):
    pass

class CustomerModel(BaseMemberModel):
    pass

class BaseRecordModel(models.Model):
    work_date = models.DateField()

    work_status = models.IntegerField()

    current_status = models.IntegerField(
        choices=CurrentStatusEnum.choices,
        default=CurrentStatusEnum.BEFORE
    )

    change_history = models.CharField(
        max_length=500,
        blank=True,
        default=''
    )

    is_work_status_changed_today = models.BooleanField(
        default=False
    )

    remarks = models.TextField(
        max_length=200,
        blank=True,
        default=''
    )

    is_remarks_changed_today = models.BooleanField(
        default=False
    )    

    clock_in_time = models.TimeField(blank=True, null=True)
    clock_out_time = models.TimeField(blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        target = getattr(self, 'staff', None) or getattr(self, 'customer', None)
        return f'{target} - {self.work_date}'

class StaffRecordModel(BaseRecordModel):
    staff = models.ForeignKey(
        StaffModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_records'
    )

    work_status = models.IntegerField(
        choices=StaffWorkStatusEnum.choices,
        default=StaffWorkStatusEnum.OFF
    )

    class Meta:
        ordering = ['staff__order']
        constraints = [
            models.UniqueConstraint(
                fields=['staff', 'work_date'],
                name='unique_staff_work_date'
            )
        ]

class CustomerRecordModel(BaseRecordModel):
    customer = models.ForeignKey(
        CustomerModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_records'
    )

    work_status = models.IntegerField(
        choices=CustomerWorkStatusEnum.choices,
        default=CustomerWorkStatusEnum.OFF
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'work_date'],
                name='unique_customer_work_date'
            )
        ] 

class BasePatternModel(models.Model):

    weekday = models.IntegerField(
        choices=WeekdayEnum.choices
    )

    remarks = models.TextField(
        max_length=200,
        blank=True,
        default=''
    )

    class Meta:
        abstract = True

    def __str__(self):
        target = getattr(self, 'staff', None) or getattr(self, 'customer', None)
        return f'{target} - {self.get_weekday_display()}'

class StaffPatternModel(BasePatternModel):
    staff = models.ForeignKey(
        StaffModel,
        on_delete=models.CASCADE,
    )

    work_status = models.IntegerField(
        choices=StaffWorkStatusEnum.choices,
        default=StaffWorkStatusEnum.OFF
    )

    class Meta:
        unique_together = ('staff', 'weekday')
        ordering = ['weekday']
    
class CustomerPatternModel(BasePatternModel):
    customer = models.ForeignKey(
        CustomerModel,
        on_delete=models.CASCADE,
    )

    work_status = models.IntegerField(
        choices=CustomerWorkStatusEnum.choices,
        default=CustomerWorkStatusEnum.OFF
    )

    class Meta:
        unique_together = ('customer', 'weekday')
        ordering = ['weekday']
    
class BaseTransportModel(models.Model):
    customer = models.ForeignKey(
        CustomerModel,
        on_delete=models.CASCADE,
    )

    transport_type = models.IntegerField(
        choices=TransportTypeEnum.choices
    )

    transport_means = models.IntegerField(
        choices=TransportMeansEnum.choices,
        blank=True,
        null=True,
    )

    place = models.CharField(
        max_length=20,
        blank=True,
        default='',
    )

    staff = models.ForeignKey(
        StaffModel,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    remarks = models.CharField(
        max_length=20,
        blank=True,
        default='',
    )

    class Meta:
        abstract = True

class TransportPatternModel(BaseTransportModel):

    weekday = models.IntegerField(
        choices=WeekdayEnum.choices
    )

    class Meta:
        unique_together = ('customer', 'weekday', 'transport_type')
        ordering = ['weekday']

    def __str__(self):
        return f'{self.customer} {self.get_weekday_display()} {self.transport_type}'

class TransportRecordModel(BaseTransportModel):
    record = models.ForeignKey(
        'CustomerRecordModel',
        on_delete=models.CASCADE,
        related_name='record_transport'
    )

    is_changed_today = models.BooleanField(
        default = False
    )

    class Meta:
        unique_together = ('record', 'transport_type')

    def __str__(self):
        return f'{self.record} - {self.get_transport_type_display()}'

class BaseSessionModel(models.Model):
    session_no = models.PositiveSmallIntegerField(null=False,default=1)

    place = models.ForeignKey(
        'PlaceModel',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)

    class Meta:
        abstract = True  # DB テーブルは作らない

class StaffSessionPatternModel(BaseSessionModel):

    staff = models.ForeignKey(
        'StaffModel',
        on_delete=models.CASCADE,
        related_name='staff_session_pattern'
    )    

    weekday = models.IntegerField(
        choices=WeekdayEnum.choices
    )

    class Meta:
        unique_together = (
            'staff',    
            'weekday',
            'session_no',
        )

    def __str__(self):
        return f'{self.staff} - {self.get_weekday_display()} - 勤務{self.session_no}'
    
class CustomerSessionPatternModel(BaseSessionModel):

    customer = models.ForeignKey(
        'CustomerModel',
        on_delete=models.CASCADE,
        related_name='customer_session_pattern'
    )    

    weekday = models.IntegerField(
        choices=WeekdayEnum.choices
    )

    class Meta:
        unique_together = (
            'customer',    
            'weekday',
            'session_no',
        )

    def __str__(self):
        return f'{self.customer} - {self.get_weekday_display()} - 勤務{self.session_no}'

class BaseSessionRecordModel(BaseSessionModel):
    is_place_changed_today = models.BooleanField(default=False)
    is_time_changed_today = models.BooleanField(default=False)

    class Meta:
        abstract = True


class StaffSessionRecordModel(BaseSessionRecordModel):

    record = models.ForeignKey(
        StaffRecordModel,
        on_delete=models.CASCADE,
        related_name='staff_session_record'
    )

    class Meta:
        unique_together = ('record', 'session_no')
        ordering = ['session_no']

    def __str__(self):
        return f'{self.record} - 勤務{self.session_no}'
    
class CustomerSessionRecordModel(BaseSessionRecordModel):

    record = models.ForeignKey(
        CustomerRecordModel,
        on_delete=models.CASCADE,
        related_name='customer_session_record'
    )

    class Meta:
        unique_together = ('record', 'session_no')
        ordering = ['session_no']

    def __str__(self):
        return f'{self.record} - 勤務{self.session_no}'

class PlaceModel(models.Model):
    name = models.CharField(
        max_length=20, 
        blank=True,
        default='',
     )
    
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order'] 

    def __str__(self):
        return self.name 
    
class PlaceRemarksModel(models.Model):

    place = models.ForeignKey(
        PlaceModel,
        on_delete=models.SET_NULL,
        null = True,
        blank=True,
    )

    work_date = models.DateField()

    remarks = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    class Meta:
        unique_together = ('place', 'work_date')

    def __str__(self):
        return f'{self.place} - {self.work_date}'

class SysAdModel(models.Model):

    auto_mode_days = models.IntegerField(
        null=False,
        blank=False,
        default=0,
    )

    validators=[
        MinValueValidator(0),
        MaxValueValidator(10),
    ],

class DayModel(models.Model):
    work_date = models.DateField()

    notice = models.TextField(
        max_length=200,
        blank=True,
        default=''
    )    

    def __str__(self):
        return f'{self.work_date}'
