document.addEventListener('DOMContentLoaded', function() {
    const googleLoginBtn = document.getElementById('googleLoginBtn');
    const loginSuccessToast = new bootstrap.Toast(document.getElementById('loginSuccessToast'), { delay: 2000 });
    const toastMessage = document.getElementById('toastMessage');

    if (googleLoginBtn) {
        const googleLoginUrl = googleLoginBtn.dataset.googleLoginUrl;
        const chatbotUrl = googleLoginBtn.dataset.chatbotUrl;
        const loginUrl = googleLoginBtn.dataset.loginUrl;

        // Google 로그인 버튼 클릭 이벤트
        googleLoginBtn.addEventListener('click', function() {
            // Google OAuth2 클라이언트 초기화
            google.accounts.id.initialize({
                client_id: 'YOUR_GOOGLE_CLIENT_ID', // 실제 클라이언트 ID로 교체 필요
                callback: handleCredentialResponse
            });

            // Google 로그인 프롬프트 표시
            google.accounts.id.prompt();
        });

        // Google 로그인 응답 처리
        function handleCredentialResponse(response) {
            // 서버로 토큰 전송
            fetch(googleLoginUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    credential: response.credential
                })
            })
            .then(response => {
                if (response.ok) {
                    // 로그인 성공
                    toastMessage.textContent = '로그인 성공! 챗봇 페이지로 이동합니다.';
                    loginSuccessToast.show();
                    
                    // 2초 후 챗봇 페이지로 이동
                    setTimeout(() => {
                        window.location.href = chatbotUrl;
                    }, 2000);
                } else {
                    // 로그인 실패
                    toastMessage.textContent = '로그인에 실패했습니다. 다시 시도해주세요.';
                    loginSuccessToast.show();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                toastMessage.textContent = '로그인 처리 중 오류가 발생했습니다.';
                loginSuccessToast.show();
            });
        }

        // CSRF 토큰 가져오기
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    }

    // 알림 버튼 클릭 이벤트 (로그인 페이지에는 없지만, base.html에 있어 js 에러 방지)
    const notificationBtn = document.getElementById('notificationBtn');
    if (notificationBtn) {
        notificationBtn.addEventListener('click', function(e) {
            e.preventDefault();
            alert('새로운 알림이 없습니다.');
        });
    }

    // 로그아웃 버튼 클릭 이벤트 (로그인 페이지에는 없지만, base.html에 있어 js 에러 방지)
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            // 로그아웃 처리
            window.location.href = '{% url "home" %}'; // 실제 URL 패턴에 맞게 수정
        });
    }
}); 