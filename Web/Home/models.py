from django.db import models

class Policies(models.Model):
    plcy_no = models.CharField(max_length=50, primary_key=True)
    plcy_nm = models.TextField()
    plcy_expln_cn = models.TextField(null=True)
    plcy_sprt_cn = models.TextField(null=True)
    plcy_aply_mthd_cn = models.TextField(null=True)
    srng_mthd_cn = models.TextField(null=True)
    sbmsn_dcmnt_cn = models.TextField(null=True)
    etc_mttr_cn = models.TextField(null=True)
    inq_cnt = models.IntegerField(default=0, null=True)
    frst_reg_dt = models.DateTimeField(null=True)
    last_mdfcn_dt = models.DateTimeField(null=True)
    aply_bgng_ymd = models.DateField(null=True)
    aply_end_ymd = models.DateField(null=True)
    sprt_trgt_min_age = models.IntegerField(null=True)
    sprt_trgt_max_age = models.IntegerField(null=True)
    mrg_stts_cd = models.CharField(max_length=10, null=True)
    plcy_major_cd = models.CharField(max_length=500, null=True)
    job_cd = models.CharField(max_length=500, null=True)
    school_cd = models.CharField(max_length=500, null=True)
    zip_cd = models.CharField(max_length=500, null=True)
    earn_cnd_se_cd = models.CharField(max_length=10, null=True)
    earn_etc_cn = models.TextField(null=True)
    add_aply_qlfcc_cn = models.TextField(null=True)
    ptcp_prp_trgt_cn = models.TextField(null=True)
    lclsf_nm = models.CharField(max_length=100, null=True)
    mclsf_nm = models.CharField(max_length=100, null=True)
    plcy_pvsn_mthd_cd = models.CharField(max_length=10, null=True)
    plcy_kywd_nm = models.TextField(null=True)
    sprvsn_inst_cd_nm = models.CharField(max_length=200, null=True)
    oper_inst_cd_nm = models.CharField(max_length=200, null=True)
    aply_prd_se_cd = models.CharField(max_length=10, null=True)
    biz_prd_se_cd = models.CharField(max_length=10, null=True)
    biz_prd_bgng_ymd = models.DateField(null=True)
    biz_prd_end_ymd = models.DateField(null=True)
    biz_prd_etc_cn = models.TextField(null=True)
    s_biz_cd = models.CharField(max_length=50, null=True)
    aply_url_addr = models.TextField(null=True)
    ref_url_addr1 = models.TextField(null=True)
    ref_url_addr2 = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.plcy_nm or self.plcy_no

    class Meta:
        db_table = 'policies'
        indexes = [
            models.Index(fields=['sprt_trgt_min_age', 'sprt_trgt_max_age'], name='idx_policies_age'),
            models.Index(fields=['aply_bgng_ymd', 'aply_end_ymd'], name='idx_policies_aply_dates'),
            models.Index(fields=['lclsf_nm', 'mclsf_nm'], name='idx_policies_classification'),
            models.Index(fields=['plcy_nm'], name='idx_policies_plcy_nm'),
        ]
        verbose_name = '정책'
        verbose_name_plural = '정책'