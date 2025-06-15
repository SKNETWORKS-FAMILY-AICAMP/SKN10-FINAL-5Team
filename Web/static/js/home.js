let currentSlide = 0;
const slider = document.getElementById('policySlider');
const slides = slider.children;
const totalSlides = slides.length;
const slidesToShow = window.innerWidth < 768 ? 1 : window.innerWidth < 1024 ? 2 : 4;

function updateSlider() {
    const offset = currentSlide * -100;
    slider.style.transform = `translateX(${offset}%)`;
}

function slideNext() {
    const maxSlide = Math.ceil(totalSlides / slidesToShow) - 1;
    if (currentSlide < maxSlide) {
        currentSlide++;
        updateSlider();
    }
}

function slidePrev() {
    if (currentSlide > 0) {
        currentSlide--;
        updateSlider();
    }
}

// 반응형 처리
window.addEventListener('resize', () => {
    const newSlidesToShow = window.innerWidth < 768 ? 1 : window.innerWidth < 1024 ? 2 : 4;
    if (newSlidesToShow !== slidesToShow) {
        currentSlide = 0;
        updateSlider();
    }
});

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
            console.error('Error fetching policy:', error);
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

// ESC 키로 모달 닫기
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closePolicyModal();
    }
});

// 모달 외부 클릭시 닫기
document.getElementById('policyModal').addEventListener('click', function(event) {
    if (event.target === this) {
        closePolicyModal();
    }
});
