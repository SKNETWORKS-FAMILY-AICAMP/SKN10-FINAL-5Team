// 현재 모달에 표시 중인 정책의 신청 URL을 저장할 변수
// 버튼 클릭 시 새 탭으로 열 때 사용
let currentPolicyUrl = '';

// 정책 번호를 매개변수로 받아 해당 정책 상세 정보를 보여주는 함수
function openPolicyModal(policyId) {
    console.log('Opening modal for policy:', policyId);
    
    const modal = document.getElementById('policyModal');
    modal.style.display = 'flex';
    
    fetch(`/api/policy/${policyId}/`)
        .then(response => {
            // 응답 응답 객체를 JSON으로 파싱하고 디버깅 로그 남김
            console.log('API Response:', response);
            return response.json();
        })
        .then(data => {
            // JSON 파싱된 데이터를 받아 사용
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
            if (data.신청url주소) {
                currentPolicyUrl = data.신청url주소;
                button.textContent = '신청하기';
                button.disabled = false;
            } else if (data.참고url주소1) {
                currentPolicyUrl = data.참고url주소1;
                button.textContent = '이동하기';
                button.disabled = false;
            } else if (data.참고url주소2) {
                currentPolicyUrl = data.참고url주소2;
                button.textContent = '이동하기';
                button.disabled = false;
            } else {
                button.textContent = '신청하기';
                button.disabled = true;
            }
        })
        .catch(error => {
            console.error('Error fetching policy details:', error);
        });
}

// 모달 숨김, 상태 초기화
function closePolicyModal() {
    const modal = document.getElementById('policyModal');
    modal.style.display = 'none';
    currentPolicyUrl = '';
}

// 모달 하단 버튼 클릭 시 URL을 새 탭으로 열기
function handlePolicyButtonClick() {
    if (currentPolicyUrl) {
        window.open(currentPolicyUrl, '_blank');
    }
}