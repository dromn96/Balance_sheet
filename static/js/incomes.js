document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.edit-icon').forEach(icon => {
    icon.addEventListener('click', (e) => {
      const row = e.target.closest('tr');
      const id = row.dataset.id;
      window.location.href = `/incomes/${id}/edit`; // Переход на страницу редактирования
    });
  });

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
});

  document.querySelectorAll('.delete-icon').forEach(icon => {
    icon.addEventListener('click', async (e) => {
      const row = e.target.closest('tr');
      const id = row.dataset.id;

      if (confirm('Вы действительно хотите удалить эту запись?')) {
        const token = document.querySelector('#token input').value;
        const response = await fetch(`/incomes/${id}/delete`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': token,
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          row.remove(); // Удаляем строку из таблицы
          alert('Запись успешно удалена');
        } else {
          alert('Ошибка при удалении записи');
        }
      }
    });
  });

  // Функция для получения CSRF токена (если нужно)
