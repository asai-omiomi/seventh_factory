from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from app.models import SysAdModel, StaffRecordModel
from app.services.create_records_common import create_records

class Command(BaseCommand):
    help = "勤務データ自動作成"

    def handle(self, *args, **options):
        sysad = SysAdModel.objects.get(pk=1)
        days = sysad.auto_mode_days

        if days <= 0:
            self.stdout.write("自動作成なし")
            return

        today = timezone.localdate()

        for i in range(1, days + 1):
            target_date = today + timedelta(days=i)

            # 重複防止（重要）
            if StaffRecordModel.objects.filter(work_date=target_date).exists():
                continue

            create_records("自動実行", target_date)

        self.stdout.write(self.style.SUCCESS("自動作成完了"))