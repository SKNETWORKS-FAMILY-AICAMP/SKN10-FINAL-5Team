// 현재 모달에 표시 중인 정책의 신청 URL을 저장할 변수
// 버튼 클릭 시 새 탭으로 열 때 사용
let currentPolicyUrl = '';

// 값이 없을 때 '공식 홈페이지 참고'로 표시하는 함수로 수정
function safeValue(val) {
    return (val === null || val === undefined || val === '') ? '공식 홈페이지 참고' : val;
}

// 정책 번호를 매개변수로 받아 해당 정책 상세 정보를 보여주는 함수
function openPolicyModal(policyId) {
    window.currentPolicyId = policyId;
    console.log('Opening modal for policy:', policyId);
    
    // 기존 모달 제거
    const existingModal = document.getElementById('policyModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // API 호출을 먼저 실행
    fetch(`/api/policy/${policyId}/`)
        .then(response => {
            // 응답 응답 객체를 JSON으로 파싱하고 디버깅 로그 남김
            console.log('API Response:', response);
            return response.json();
        })
        .then(data => {
            // JSON 파싱된 데이터를 받아 사용
            console.log('Policy data:', data);
            
            // 로그인된 경우에만 관심도 저장
            function saveInterest(policyId, interestStatus, retry) {
                fetch('/chatbot/api/interest/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({ plcy_no: policyId, interest_status: interestStatus })
                })
                .then(res => res.json())
                .then(res => {
                    if (res.status === 'token_refreshed' && !retry) {
                        // 토큰 갱신 후 1회만 재시도
                        saveInterest(policyId, interestStatus, true);
                        return;
                    }
                    console.log('관심도 저장 응답:', res);
                })
                .catch(err => { console.error('관심도 저장 에러:', err); });
            }
            saveInterest(policyId, '확인', false);
            
            // 지연 후 모달 생성 및 표시
            setTimeout(() => {
                // 새로운 모달 생성
                const newModal = document.createElement('div');
                newModal.id = 'policyModal';
                newModal.className = 'fixed inset-0 bg-black bg-opacity-50 items-center justify-center z-50';
                newModal.style.display = 'flex';
                
                newModal.innerHTML = `
                    <div class="bg-white rounded-xl p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto relative">
                        <div class="flex justify-between items-start mb-6">
                            <h2 id="modalPolicyName" class="text-2xl font-bold text-gray-800">
                                ${safeValue(data.plcy_nm)}</h2>
                            <button onclick="closePolicyModal()" class="text-gray-500 hover:text-gray-700 absolute top-4 right-4">
                                <span class="material-icons">close</span>
                            </button>
                        </div>
                        
                        <div class="space-y-6">
                            <div>
                                <span id="modalPolicyCategory" class="text-sm font-medium px-3 py-1 rounded-full ${data.category_color.bg} ${data.category_color.text}">${safeValue(data.mclsf_nm)}</span>
                                <span id="modalPolicyZipCd" class="text-sm font-medium px-3 py-1 rounded-full bg-gray-200 text-gray-700 ml-2">${safeValue(data.zip_cd)}</span>
                            </div>
                            
                            <div>
                                <h3 class="text-lg font-semibold text-gray-800 mb-2">정책 설명</h3>
                                <p id="modalPolicyDescription" class="text-gray-600 whitespace-pre-line">${safeValue(data.plcy_expln_cn)}</p>
                            </div>
                            
                            <div>
                                <h3 class="text-lg font-semibold text-gray-800 mb-2">지원 내용</h3>
                                <p id="modalPolicySupport" class="text-gray-600 whitespace-pre-line">${safeValue(data.plcy_sprt_cn)}</p>
                            </div>
                            
                            <div>
                                <h3 class="text-lg font-semibold text-gray-800 mb-2">신청 방법</h3>
                                <p id="modalPolicyApplyMethod" class="text-gray-600 whitespace-pre-line">${safeValue(data.plcy_aply_mthd_cn)}</p>
                            </div>
                            
                            <div>
                                <h3 class="text-lg font-semibold text-gray-800 mb-2">제출 서류</h3>
                                <p id="modalPolicyDocuments" class="text-gray-600 whitespace-pre-line">${safeValue(data.sbmsn_dcmnt_cn)}</p>
                            </div>
                            
                            <div class="flex justify-between text-sm text-gray-500">
                                <div>
                                    <span>조회수: </span>
                                    <span id="modalPolicyViews">${safeValue(data.inq_cnt)}</span>
                                </div>
                                <div>
                                    <span>신청기간: </span>
                                    <span id="modalPolicyPeriod">${data.aply_bgng_ymd ? new Date(data.aply_bgng_ymd).toLocaleDateString() : '미제공'} ~ ${data.aply_end_ymd ? new Date(data.aply_end_ymd).toLocaleDateString() : '미제공'}</span>
                                </div>
                            </div>
                            
                            <div class="flex justify-end mt-6">
                                <button id="modalPolicyButton" onclick="handlePolicyButtonClick()" 
                                        class="px-6 py-2 ${data.aply_url_addr || data.ref_url_addr1 || data.ref_url_addr2 ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-400 text-white cursor-not-allowed'} rounded-lg transition-colors" 
                                        ${!(data.aply_url_addr || data.ref_url_addr1 || data.ref_url_addr2) ? 'disabled' : ''}>
                                    ${data.aply_url_addr ? '신청하기' : data.ref_url_addr1 || data.ref_url_addr2 ? '이동하기' : '신청하기'}
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                
                // 새 모달을 body에 추가
                document.body.appendChild(newModal);
                
                // URL 설정
                if (data.aply_url_addr) {
                    currentPolicyUrl = data.aply_url_addr;
                } else if (data.ref_url_addr1) {
                    currentPolicyUrl = data.ref_url_addr1;
                } else if (data.ref_url_addr2) {
                    currentPolicyUrl = data.ref_url_addr2;
                } else {
                    currentPolicyUrl = '';
                }
                
            }, 50); // 300ms 지연 후 모달 표시
        })
        .catch(error => {
            console.error('Error fetching policy details:', error);
            // 에러 발생 시에도 지연 후 모달 표시
            setTimeout(() => {
                const newModal = document.createElement('div');
                newModal.id = 'policyModal';
                newModal.className = 'fixed inset-0 bg-black bg-opacity-50 items-center justify-center z-50';
                newModal.style.display = 'flex';
                
                newModal.innerHTML = `
                    <div class="bg-white rounded-xl p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto relative">
                        <div class="flex justify-between items-start mb-6">
                            <h2 id="modalPolicyName" class="text-2xl font-bold text-gray-800">오류 발생</h2>
                            <button onclick="closePolicyModal()" class="text-gray-500 hover:text-gray-700 absolute top-4 right-4">
                                <span class="material-icons">close</span>
                            </button>
                        </div>
                        
                        <div class="space-y-6">
                            <div>
                                <p class="text-gray-600">정책 정보를 불러오는 중 오류가 발생했습니다.</p>
                            </div>
                            
                            <div class="flex justify-end mt-6">
                                <button onclick="closePolicyModal()" class="px-6 py-2 bg-gray-400 text-white rounded-lg cursor-not-allowed" disabled>
                                    닫기
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(newModal);
            }, 50);
        });
}

// 모달 숨김, 상태 초기화
function closePolicyModal() {
    const modal = document.getElementById('policyModal');
    if (modal) {
        modal.remove();
    }
    currentPolicyUrl = '';
}

// 모달 하단 버튼 클릭 시 URL을 새 탭으로 열기
function handlePolicyButtonClick() {
    if (currentPolicyUrl) {
        // 정책 신청/이동 버튼 클릭 시 '신청' 상태로 저장
        const modal = document.getElementById('policyModal');
        if (modal) {
            const policyNameElem = modal.querySelector('#modalPolicyName');
            if (policyNameElem) {
                const policyName = policyNameElem.textContent;
                // 정책 번호는 모달에 숨겨진 데이터로 저장하거나, openPolicyModal에서 전역 변수로 저장 필요
                // 여기서는 policyId를 전역 변수로 저장한다고 가정
                if (window.currentPolicyId) {
                    function saveInterestApply(policyId, retry) {
                        fetch('/chatbot/api/interest/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || ''
                            },
                            credentials: 'same-origin',
                            body: JSON.stringify({ plcy_no: policyId, interest_status: '신청' })
                        })
                        .then(res => res.json())
                        .then(res => {
                            if (res.status === 'token_refreshed' && !retry) {
                                saveInterestApply(policyId, true);
                                return;
                            }
                            console.log('관심도 저장 응답:', res);
                        })
                        .catch(err => { console.error('관심도 저장 에러:', err); });
                    }
                    saveInterestApply(window.currentPolicyId, false);
                }
            }
        }
        window.open(currentPolicyUrl, '_blank');
    }
}