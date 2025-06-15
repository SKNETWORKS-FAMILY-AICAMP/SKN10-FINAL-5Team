from django.db import models


class Policy(models.Model):
    plcyNo = models.CharField(max_length=100, primary_key=True, verbose_name='정책번호')
    plcyNm = models.CharField(max_length=200, null=True, verbose_name='정책명')
    plcyExplnCn = models.TextField(null=True, verbose_name='정책설명내용')
    lclsNm = models.CharField(max_length=100, null=True, verbose_name='정책분류명')
    plcySprtCn = models.TextField(null=True, verbose_name='정책지원내용')
    plcyAplyMthdCn = models.TextField(null=True, verbose_name='정책신청방법내용')
    aplyUrlAddr = models.TextField(null=True, verbose_name='신청URL주소')
    sbmsnDcmntCn = models.TextField(null=True, verbose_name='제출서류내용')
    refUrlAddr1 = models.TextField(null=True, verbose_name='참고URL주소1')
    refUrlAddr2 = models.TextField(null=True, verbose_name='참고URL주소2')
    inqCnt = models.IntegerField(null=True, verbose_name='조회수')
    aplyStartYmd = models.DateField(null=True, verbose_name='신청시작일자')
    aplyEndYmd = models.DateField(null=True, verbose_name='신청종료일자')

    def __str__(self):
        return self.plcyNm or self.plcyNo
    

class PolicyRaw(models.Model):
    정책번호 = models.CharField(max_length=100, primary_key=True)
    정책제공방법코드 = models.CharField(max_length=100, null=True)
    정책명 = models.CharField(max_length=200, null=True)
    정책키워드명 = models.CharField(max_length=200, null=True)
    정책설명내용 = models.TextField(null=True)
    정책대분류명 = models.CharField(max_length=100, null=True)
    정책중분류명 = models.CharField(max_length=100, null=True)
    정책지원내용 = models.TextField(null=True)
    주관기관코드명 = models.CharField(max_length=100, null=True)
    운영기관코드명 = models.CharField(max_length=100, null=True)
    신청기간구분코드 = models.CharField(max_length=100, null=True)
    사업기간구분코드 = models.CharField(max_length=100, null=True)
    사업기간시작일자 = models.DateField(null=True)
    사업기간종료일자 = models.DateField(null=True)
    사업기간기타내용 = models.TextField(null=True)
    정책신청방법내용 = models.TextField(null=True)
    심사방법내용 = models.TextField(null=True)
    신청url주소 = models.TextField(null=True)
    제출서류내용 = models.TextField(null=True)
    기타사항내용 = models.TextField(null=True)
    참고url주소1 = models.TextField(null=True)
    참고url주소2 = models.TextField(null=True)
    지원도착순서여부 = models.CharField(max_length=10, null=True)
    지원대상최소연령 = models.IntegerField(null=True)
    지원대상최대연령 = models.IntegerField(null=True)
    결혼상태코드 = models.CharField(max_length=100, null=True)
    소득조건구분코드 = models.CharField(max_length=100, null=True)
    소득기타내용 = models.TextField(null=True)
    추가신청자격조건내용 = models.TextField(null=True)
    참여제안대상내용 = models.TextField(null=True)
    조회수 = models.IntegerField(null=True)
    정책거주지역코드 = models.CharField(max_length=100, null=True)
    정책전공요건코드 = models.CharField(max_length=100, null=True)
    정책취업요건코드 = models.CharField(max_length=100, null=True)
    정책학력요건코드 = models.CharField(max_length=100, null=True)
    정책특화요건코드 = models.CharField(max_length=100, null=True)
    신청시작일자 = models.DateField(null=True)
    신청종료일자 = models.DateField(null=True)

    def __str__(self):
        return self.정책명 or self.정책번호

    class Meta:
        db_table = 'policy_raw'
        verbose_name = '정책 원본 데이터'
        verbose_name_plural = '정책 원본 데이터'
