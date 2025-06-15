let currentPolicyUrl = '';

function openPolicyModal(policyId) {
    console.log('Opening modal for policy:', policyId);
    
    const modal = document.getElementById('policyModal');
    modal.style.display = 'flex';
    
    fetch(`/api/policy/${policyId}/`)
        .then(response => {
            console.log('API Response:', response);
            return response.json();
        })
        .then(data => {
            console.log('Policy data:', data);
            
            document.getElementById('modalPolicyName').textContent = data.정책명;
            document.getElementById('modalPolicyCategory').textContent = data.정책중분류명;
            document.getElementById('modalPolicyDescription').textContent = data.정책설명내용;
            document.getElementById('modalPolicySupport').textContent = data.정책지원내용;
            document.getElementById('modalPolicyApplyMethod').textContent = data.정책신청방법내용;
            document.getElementById('modalPolicyDocuments').textContent = data.제출서류내용;
            document.getElementById('modalPolicyViews').textContent = data.조회수;
            
            const startDate = data.신청시작일자 ? new Date(data.신청시작일자).toLocaleDateString() : '';
            const endDate = data.신청종료일자 ? new Date(data.신청종료일자).toLocaleDateString() : '';
            document.getElementById('modalPolicyPeriod').textContent = `${startDate} ~ ${endDate}`;
            
            // 정책중분류명 태그에 색상 적용
            const modalCategorySpan = document.getElementById('modalPolicyCategory');
            modalCategorySpan.textContent = data.정책중분류명;
            modalCategorySpan.className = `text-sm font-medium px-3 py-1 rounded-full ${data.category_color.bg} ${data.category_color.text}`;
            
            const button = document.getElementById('modalPolicyButton');
            if (data.정책URL) {
                currentPolicyUrl = data.정책URL;
                button.textContent = '정책 신청하기';
                button.disabled = false;
            } else {
                currentPolicyUrl = '';
                button.textContent = '신청 링크 없음';
                button.disabled = true;
            }
        })
        .catch(error => {
            console.error('Error fetching policy details:', error);
        });
}

function closePolicyModal() {
    const modal = document.getElementById('policyModal');
    modal.style.display = 'none';
    currentPolicyUrl = '';
}

function handlePolicyButtonClick() {
    if (currentPolicyUrl) {
        window.open(currentPolicyUrl, '_blank');
    }
} 