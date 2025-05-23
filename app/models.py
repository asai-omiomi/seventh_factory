# models.py
from django.db import models
from enum import Enum
from django.contrib.auth.models import User

WORK_SESSION_COUNT = 4

class StaffWorkStatusEnum(Enum):
    ON = 0
    OFF = 1
    OFF_WITH_PAY = 2

STAFF_WORK_STATUS_CHOICES = [
    (StaffWorkStatusEnum.ON.value,'出勤'),
    (StaffWorkStatusEnum.OFF.value,'欠勤'),    
    (StaffWorkStatusEnum.OFF_WITH_PAY.value,'有給'),  
]

class CustomerWorkStatusEnum(Enum):
    OFFICE = 0
    HOME = 1
    OFF = 2

CUSTOMER_WORK_STATUS_CHOICES = [
    (CustomerWorkStatusEnum.OFFICE.value,'通所'),
    (CustomerWorkStatusEnum.HOME.value,'在宅'),
    (CustomerWorkStatusEnum.OFF.value,'欠席'),
]

class TransportMeansEnum(Enum):
    TRANSFER = 0
    CAR = 1
    BUS = 2
    BICYCLE = 3
    WALK = 4
    MOTORCYCLE = 5
    OTHERS = 6

TRANSPORT_MEANS_CHOICES = [
    (TransportMeansEnum.TRANSFER.value, '送迎'),
    (TransportMeansEnum.CAR.value, '車'),
    (TransportMeansEnum.BUS.value, 'バス'),
    (TransportMeansEnum.BICYCLE.value, '自転車'),
    (TransportMeansEnum.WALK.value, '徒歩'),
    (TransportMeansEnum.MOTORCYCLE.value, 'バイク'),
    (TransportMeansEnum.OTHERS.value, 'その他'),   
]

class LunchEnum(Enum):
    ORDERED_LUNCH_BOX = 0
    BYO_LUNCH_BOX = 1
    NO_LUNCH_BOX = 2

LUNCH_CHOICES = [
    (LunchEnum.ORDERED_LUNCH_BOX.value, '有り(注文)'),
    (LunchEnum.BYO_LUNCH_BOX.value, '有り(持参)'),
    (LunchEnum.NO_LUNCH_BOX.value, '無し'), 
]

def get_lunch_display(lunch_value):
    if lunch_value == LunchEnum.ORDERED_LUNCH_BOX.value:
        return "〇"

    elif lunch_value == LunchEnum.BYO_LUNCH_BOX.value:
        return "〇\n(持参)"     

    elif lunch_value == LunchEnum.NO_LUNCH_BOX.value:
        return ""    
    else:
        return ""

class CurrentStatusEnum(Enum):
    BEFORE_WORK = 0    #出勤前
    AFTER_WORK = 5     #退勤後

class WorkPlaceModel(models.Model):
    name = models.CharField(
        max_length=20, 
        blank=True,
        null=True,
     )

    area = models.CharField(
        max_length=20, 
        blank=True,
        null=True,
     )
    
    def __str__(self):
        return self.name 
    
class CompanyCarModel(models.Model):
    name = models.CharField(
        max_length=20, 
        blank=False,
        null=False,
        default=''
     )
    
    def __str__(self):
        return self.name

class StaffModel(models.Model):

    name = models.CharField(
        max_length=20, 
        blank=False,
        null=False,
        default=''
    )
    
    order = models.IntegerField(
        blank=False, 
        null=False,
    )
        
    work_status_mon = models.IntegerField(
        blank=False, 
        null=False,
        choices=STAFF_WORK_STATUS_CHOICES,
        default=StaffWorkStatusEnum.ON.value
    )

    work_status_tue = models.IntegerField(
        blank=False, 
        null=False,
        choices=STAFF_WORK_STATUS_CHOICES,
        default=StaffWorkStatusEnum.ON.value
    )

    work_status_wed = models.IntegerField(
        blank=False, 
        null=False,
        choices=STAFF_WORK_STATUS_CHOICES,
        default=StaffWorkStatusEnum.ON.value
    )
    
    work_status_thu = models.IntegerField(
        blank=False, 
        null=False,
        choices=STAFF_WORK_STATUS_CHOICES,
        default=StaffWorkStatusEnum.ON.value
    )

    work_status_fri = models.IntegerField(
        blank=False, 
        null=False,
        choices=STAFF_WORK_STATUS_CHOICES,
        default=StaffWorkStatusEnum.ON.value
    )

    work_status_sat = models.IntegerField(
        blank=False, 
        null=False,
        choices=STAFF_WORK_STATUS_CHOICES,
        default=StaffWorkStatusEnum.OFF.value
    )

    work_status_sun = models.IntegerField(
        blank=False, 
        null=False,
        choices=STAFF_WORK_STATUS_CHOICES,
        default=StaffWorkStatusEnum.OFF.value
    )

    for i in range(1, WORK_SESSION_COUNT + 1):
        locals()[f'work{i}_start_time'] = models.TimeField(
            blank=True, null=True
        )
        locals()[f'work{i}_end_time'] = models.TimeField(
            blank=True, null=True
        )
        locals()[f'work{i}_place'] = models.ForeignKey(
            WorkPlaceModel,
            on_delete=models.SET_NULL,
            blank=True,
            null=True,
            related_name=f'staff_work{i}_place'
        )
    del i 
 
    lunch = models.IntegerField(
        blank=True,
        null=True,
        choices=LUNCH_CHOICES,
    )
    
    eat_lunch_at = models.IntegerField(
        blank=True,
        null=True,
        default=1
    )  

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.pk:  # 新規作成時
            max_order = StaffModel.objects.aggregate(models.Max('order'))['order__max']
            self.order = max_order + 1 if max_order is not None else 1
        super().save(*args, **kwargs)

class StaffWorkModel(models.Model):
    class Meta:
        unique_together = ('staff', 'work_date')
        
    staff = models.ForeignKey(
        StaffModel,
        on_delete=models.SET_NULL,
        null = True,
        related_name='staff'
    )

    staff_name = models.CharField(
        max_length=20, 
        blank=True, 
        null=True
    )

    work_date = models.DateField()

    work_status = models.IntegerField(
        blank=True, 
        null=True,
        choices=STAFF_WORK_STATUS_CHOICES,
    )

    for i in range(1, WORK_SESSION_COUNT + 1):
        locals()[f'work{i}_start_time'] = models.TimeField(
            blank=True, null=True
        )
        locals()[f'work{i}_end_time'] = models.TimeField(
            blank=True, null=True
        )
        locals()[f'work{i}_place'] = models.ForeignKey(
            WorkPlaceModel,
            on_delete=models.SET_NULL,
            blank=True,
            null=True,
            related_name=f'staff_w_work{i}_place'
        )
    del i 

    lunch = models.IntegerField(
        blank=True,
        null=True,
        choices=LUNCH_CHOICES, 
    )

    eat_lunch_at = models.IntegerField(
        blank=True,
        null=True,
        default=1
    )  

    def __str__(self):
        return f'{self.staff_name or "Unknown"} - {self.work_date}'
    
    def save(self, *args, **kwargs):
        if self.staff and not self.staff_name:
            self.staff_name = self.staff.name
        super().save(*args, **kwargs)

    def get_work_status_display(self):
        return dict(STAFF_WORK_STATUS_CHOICES).get(self.work_status, "未設定")
    
    def get_lunch_display(self):
        return get_lunch_display(self.lunch)

class CustomerModel(models.Model):
    name = models.CharField(
        max_length=20, 
        blank=False,
        null=False,
        default=''
     )
    
    order = models.IntegerField(
        blank=False, 
        null=False,
    )
    
    morning_transport_means = models.IntegerField(
        blank=True, 
        null=True,
        choices=TRANSPORT_MEANS_CHOICES,
    )

    pickup_place = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )
    pickup_staff = models.ForeignKey(
        StaffModel,
        on_delete=models.SET_NULL,
        blank=True,
        null = True,
        related_name='pickup_staff'
    )

    pickup_time = models.TimeField(
        blank=True,
        null=True,
    )

    pickup_car = models.ForeignKey(
        CompanyCarModel,
        on_delete=models.SET_NULL,
        blank=True,
        null = True,
        related_name='pickup_car'
    )

    # 帰り
    return_transport_means = models.IntegerField(
        blank=True, 
        null=True,
        choices=TRANSPORT_MEANS_CHOICES,
    )

    dropoff_place = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )
    dropoff_staff = models.ForeignKey(
        StaffModel,
        on_delete=models.SET_NULL,
        blank=True,
        null = True,
        related_name='dropoff_staff'
    )

    dropoff_time = models.TimeField(
        blank=True,
        null=True,
    )

    dropoff_car = models.ForeignKey(
        CompanyCarModel,
        on_delete=models.SET_NULL,
        blank=True,
        null = True,
        related_name='dropoff_car'
    )

    # 勤務
    work_status_mon = models.IntegerField(
        blank=False, 
        null=False,
        choices=CUSTOMER_WORK_STATUS_CHOICES,
        default=CustomerWorkStatusEnum.OFFICE.value
    )

    work_status_tue = models.IntegerField(
        blank=False, 
        null=False,
        choices=CUSTOMER_WORK_STATUS_CHOICES,
        default=CustomerWorkStatusEnum.OFFICE.value
    )

    work_status_wed = models.IntegerField(
        blank=False, 
        null=False,
        choices=CUSTOMER_WORK_STATUS_CHOICES,
        default=CustomerWorkStatusEnum.OFFICE.value
    )

    work_status_thu = models.IntegerField(
        blank=False, 
        null=False,
        choices=CUSTOMER_WORK_STATUS_CHOICES,
        default=CustomerWorkStatusEnum.OFFICE.value
    )

    work_status_fri = models.IntegerField(
        blank=False, 
        null=False,
        choices=CUSTOMER_WORK_STATUS_CHOICES,
        default=CustomerWorkStatusEnum.OFFICE.value
    )

    work_status_sat = models.IntegerField(
        blank=False, 
        null=False,
        choices=CUSTOMER_WORK_STATUS_CHOICES,
        default=CustomerWorkStatusEnum.OFF.value
    )

    work_status_sun = models.IntegerField(
        blank=False, 
        null=False,
        choices=CUSTOMER_WORK_STATUS_CHOICES,
        default=CustomerWorkStatusEnum.OFF.value
    )

    for i in range(1, WORK_SESSION_COUNT + 1):
        locals()[f'work{i}_start_time'] = models.TimeField(
            blank=True, null=True
        )
        locals()[f'work{i}_end_time'] = models.TimeField(
            blank=True, null=True
        )
        locals()[f'work{i}_place'] = models.ForeignKey(
            WorkPlaceModel,
            on_delete=models.SET_NULL,
            blank=True,
            null=True,
            related_name=f'customer_work{i}_place'
        )
    del i 

    lunch = models.IntegerField(
        blank=True,
        null=True,
        choices=LUNCH_CHOICES, 
    )
    
    eat_lunch_at = models.IntegerField(
        blank=True,
        null=True,
        default=1
    )  

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.pk:  # 新規作成時
            max_order = CustomerModel.objects.aggregate(models.Max('order'))['order__max']
            self.order = max_order + 1 if max_order is not None else 1
        super().save(*args, **kwargs)

class CustomerWorkModel(models.Model):
    class Meta:
        unique_together = ('customer', 'work_date')
        
    customer = models.ForeignKey(
        CustomerModel,
        on_delete=models.SET_NULL,
        null = True,
        blank=True,
    )

    customer_name = models.CharField(
        max_length=20, 
        blank=True, 
        null=True
    )

    work_date = models.DateField()

    work_status = models.IntegerField(
        blank=False, 
        null=True,
        choices=CUSTOMER_WORK_STATUS_CHOICES,
    )   

    current_status = models.IntegerField(
        blank=False,
        null=False,
        default=CurrentStatusEnum.BEFORE_WORK.value
    )

    morning_transport_means = models.IntegerField(
        blank=True, 
        null=True,
        choices=TRANSPORT_MEANS_CHOICES,
    )

    pickup_place = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )
    pickup_staff = models.ForeignKey(
        StaffModel,
        on_delete=models.SET_NULL,
        blank=True,
        null = True,
        related_name='work_pickup_staff'
    )

    pickup_time = models.TimeField(
        blank=True,
        null=True,
    )

    pickup_car = models.ForeignKey(
        CompanyCarModel,
        on_delete=models.SET_NULL,
        blank=True,
        null = True,
        related_name='work_pickup_car'
    )

    # 帰り
    return_transport_means = models.IntegerField(
        blank=True, 
        null=True,
        choices=TRANSPORT_MEANS_CHOICES,
    )

    dropoff_place = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )
    
    dropoff_staff = models.ForeignKey(
        StaffModel,
        on_delete=models.SET_NULL,
        blank=True,
        null = True,
        related_name='work_dropoff_staff'
    )

    dropoff_time = models.TimeField(
        blank=True,
        null=True,
    )

    dropoff_car = models.ForeignKey(
        CompanyCarModel,
        on_delete=models.SET_NULL,
        blank=True,
        null = True,
        related_name='work_dropoff_car'
    )

    for i in range(1, WORK_SESSION_COUNT + 1):
        locals()[f'work{i}_start_time'] = models.TimeField(
            blank=True, null=True
        )
        locals()[f'work{i}_end_time'] = models.TimeField(
            blank=True, null=True
        )
        locals()[f'work{i}_place'] = models.ForeignKey(
            WorkPlaceModel,
            on_delete=models.SET_NULL,
            blank=True,
            null=True,
            related_name=f'customer_w_work{i}_place'
        )
    del i 
    
    lunch = models.IntegerField(
        blank=True,
        null=True,
        choices=LUNCH_CHOICES, 
    )

    eat_lunch_at = models.IntegerField(
        blank=True,
        null=True,
        default=1
    )  

    def __str__(self):
        return f'{self.customer_name or "Unknown"} - {self.work_date}'
    
    def save(self, *args, **kwargs):
        if self.customer and not self.customer_name:
            self.customer_name = self.customer.name
        super().save(*args, **kwargs)

    def get_work_status_display(self):
        return dict(CUSTOMER_WORK_STATUS_CHOICES).get(self.work_status, '未設定')
    
    def get_current_status_display(self):
        if self.current_status == CurrentStatusEnum.BEFORE_WORK.value:
            return "出勤前"
        elif self.current_status == CurrentStatusEnum.AFTER_WORK.value:
            return "退勤済"     
        else:
            field_name = f"work{self.current_status}_place"
            return getattr(self, field_name, "")
    
    def get_morning_transport_display(self):
        return dict(TRANSPORT_MEANS_CHOICES).get(self.morning_transport_means, "")

    def get_return_transport_display(self):
        return dict(TRANSPORT_MEANS_CHOICES).get(self.return_transport_means, "")
    
    def get_lunch_display(self):
        return get_lunch_display(self.lunch)
    
class PlaceRemarksModel(models.Model):
    class Meta:
        unique_together = ('place', 'work_date')
        
    place = models.ForeignKey(
        WorkPlaceModel,
        on_delete=models.SET_NULL,
        null = True,
        blank=True,
    )

    work_date = models.DateField()

    remarks = models.CharField(
        max_length=100,
        blank=True,
        null=False,
        default=""
    )

    def __str__(self):
        return f'{self.place} - {self.work_date}'

class LogModel(models.Model):
    dateTime = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="logs"
    )

    text = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    def __str__(self):
        return f'{self.dateTime} - {self.user.username} - {self.text}'


