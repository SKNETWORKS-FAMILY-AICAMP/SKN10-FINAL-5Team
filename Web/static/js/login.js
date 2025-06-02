document.addEventListener('DOMContentLoaded', function() {
    const naverLoginBtn = document.getElementById('naver-login-btn');
    const loginSuccessToast = document.getElementById('login-success-toast');

    if (naverLoginBtn) {
        naverLoginBtn.addEventListener('click', function(event) {
            event.preventDefault();
            // 네이버 OAuth 인증 프로세스 시작
            // TODO: 실제 네이버 OAuth 인증 URL로 변경 필요
            window.location.href = 'YOUR_NAVER_OAUTH_LOGIN_URL';
        });
    }

    // 로그인 성공 후 토스트 메시지 표시 및 리다이렉션 (예시)
    // 실제로는 백엔드로부터 로그인 성공 응답을 받은 후 호출됩니다.
    function showLoginSuccessToastAndRedirect() {
        if (loginSuccessToast) {
            const toast = new bootstrap.Toast(loginSuccessToast);
            toast.show();

            // 2초 후 메인 페이지로 리다이렉션
            setTimeout(function() {
                // TODO: 실제 메인 페이지 URL로 변경 필요
                window.location.href = 'YOUR_MAIN_PAGE_URL';
            }, 2000);
        }
    }

    // 예시: 페이지 로드 시 URL 파라미터 등을 확인하여 로그인 성공 여부를 판단하고
    // showLoginSuccessToastAndRedirect 함수를 호출하는 로직 추가 필요
    // 예를 들어, 네이버 OAuth 리다이렉션 후 URL에 success=true 파라미터가 있다면:
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('login') === 'success') {
         // TODO: 실제 사용자 이름 가져오는 로직 필요
        const userName = urlParams.get('username') || '사용자님';
        const toastBody = loginSuccessToast.querySelector('.toast-body');
        if(toastBody) {
             toastBody.innerText = `로그인 성공! ${userName} 안녕하세요!`;
        }
        showLoginSuccessToastAndRedirect();
    }
});
