// 알림 기능 JavaScript
// 필요한 URL은 window.NOTI_COUNT_URL, window.NOTI_READ_URL, window.CHATBOT_URL로 전달받아 사용

document.addEventListener('DOMContentLoaded', function() {
  const notificationBtn = document.getElementById('notification-btn');
  const notificationDropdown = document.getElementById('notification-dropdown');
  const notificationDot = document.getElementById('notification-dot');
  const notificationContent = document.getElementById('notification-content');
  const closeNotification = document.getElementById('close-notification');
  
  let notificationCount = 0;
  let isDropdownOpen = false;

  // 알림 개수 가져오기 (토큰 갱신 재요청 로직 포함)
  async function fetchNotificationCount(retry = false) {
    try {
      const response = await fetch(window.NOTI_COUNT_URL, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      const data = await response.json();
      
      // 토큰 갱신 상태인 경우 재요청
      if (data.status === 'token_refreshed' && !retry) {
        console.log('토큰이 갱신되었습니다. 알림 개수를 다시 요청합니다.');
        fetchNotificationCount(true);
        return;
      }
      
      notificationCount = data.count;
      const isNew = data.is_new;
      updateNotificationUI(isNew);
    } catch (error) {
      console.error('알림 개수 가져오기 실패:', error);
    }
  }

  // 알림 UI 업데이트
  function updateNotificationUI(isNew = true) {
    if (notificationCount > 0) {
      if (isNew) {
        notificationDot.classList.remove('hidden');
      } else {
        notificationDot.classList.add('hidden');
      }
    } else {
      notificationDot.classList.add('hidden');
    }
  }

  // 알림 드롭다운 토글
  function toggleNotificationDropdown() {
    if (isDropdownOpen) {
      notificationDropdown.classList.add('hidden');
      isDropdownOpen = false;
    } else {
      notificationDropdown.classList.remove('hidden');
      isDropdownOpen = true;
      updateNotificationContent();
    }
  }

  // 알림 읽음 처리 (토큰 갱신 재요청 로직 포함)
  async function markNotificationsAsRead(retry = false) {
    try {
      const response = await fetch(window.NOTI_READ_URL, {
        method: 'POST',
        headers: {
          'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content'),
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      const data = await response.json();
      
      // 토큰 갱신 상태인 경우 재요청
      if (data.status === 'token_refreshed' && !retry) {
        console.log('토큰이 갱신되었습니다. 알림 읽음 처리를 다시 요청합니다.');
        markNotificationsAsRead(true);
        return;
      }
      
      notificationDot.classList.add('hidden');
    } catch (error) {
      console.error('알림 읽음 처리 실패:', error);
    }
  }

  // 알림 내용 업데이트
  function updateNotificationContent() {
    if (notificationCount > 0) {
      const isRead = notificationDot.classList.contains('hidden');
      const bgColor = isRead ? 'bg-gray-50' : 'bg-blue-50';
      const textColor = isRead ? 'text-gray-700' : 'text-blue-800';
      const buttonColor = isRead ? 'text-gray-600 hover:text-gray-800' : 'text-blue-600 hover:text-blue-800';
      
      notificationContent.innerHTML = `
        <div class="mb-3 p-3 ${bgColor} rounded-lg">
          <p class="${textColor} font-medium">맞춤 정책이 ${notificationCount}개 있습니다!</p>
          <button id="go-to-chatbot" class="mt-2 ${buttonColor} underline text-sm">
            챗봇에서 확인하기
          </button>
        </div>
      `;
      document.getElementById('go-to-chatbot').addEventListener('click', function() {
        window.location.href = window.CHATBOT_URL + '?message=나에게 맞는 정책 찾아줘';
      });
    } else {
      notificationContent.innerHTML = `
        <div class="text-center py-4">
          <p class="text-gray-500">맞춤 업데이트 정책이 없습니다.</p>
        </div>
      `;
    }
  }

  // 이벤트 리스너 등록
  if (notificationBtn) {
    notificationBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      toggleNotificationDropdown();
      if (notificationCount > 0) {
        markNotificationsAsRead();
        notificationDot.classList.add('hidden');
      }
    });
  }

  if (closeNotification) {
    closeNotification.addEventListener('click', function() {
      notificationDropdown.classList.add('hidden');
      isDropdownOpen = false;
    });
  }

  document.addEventListener('click', function(e) {
    if (!notificationBtn.contains(e.target) && !notificationDropdown.contains(e.target)) {
      notificationDropdown.classList.add('hidden');
      isDropdownOpen = false;
    }
  });

  fetchNotificationCount();
}); 