document.addEventListener('DOMContentLoaded', () => {
  if (!window.gridjs || !window.gridjs.Grid) {
    console.error('Grid.js failed to load; showing the original HTML tables.');
    return;
  }

  const language = {
    search: { placeholder: 'Поиск...' },
    pagination: {
      previous: 'Назад',
      next: 'Вперёд',
      showing: 'Показано',
      results: () => 'записей',
    },
    noRecordsFound: 'Записи не найдены',
  };
  const moneyFormatter = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const formatMoney = (value) => {
    const rawValue = String(value).trim();
    if (!rawValue) return '';

    const amount = Number(rawValue.replace(/[₽\s\u00a0\u202f]/g, '').replace(',', '.'));
    if (!Number.isFinite(amount)) {
      console.error(`Invalid monetary value: ${value}`);
      return rawValue;
    }

    return `${moneyFormatter.format(amount)}\u00a0₽`;
  };
  const tableCellStyles = {
    th: { 'padding-left': '5px', 'padding-right': '0' },
    td: { 'padding-left': '5px', 'padding-right': '0' },
  };

  document.querySelectorAll('#expensesTable').forEach((table) => {
    const headers = Array.from(table.querySelectorAll('thead th'), (cell) => cell.textContent.trim());
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const hasActions = Boolean(table.dataset.editBase && table.dataset.deleteBase);
    const amountColumn = headers.findIndex((header) => /стоимость|сумма дохода/i.test(header));
    const columns = headers.map((name, index) => {
      const column = { name, sort: true };

      if (hasActions && index === 0) {
        column.formatter = (id) => {
          if (!id) return '';
          return gridjs.html(
            `<div class="gridjs-record-actions">
              <a href="${table.dataset.editBase}${id}/edit" title="Редактировать">
                <img src="${table.dataset.editIcon}" alt="Редактировать" class="icon-button">
              </a>
              <a href="#" class="gridjs-delete-icon" data-delete-url="${table.dataset.deleteBase}${id}/delete" title="Удалить">
                <img src="${table.dataset.deleteIcon}" alt="Удалить" class="icon-button">
              </a>
            </div>`
          );
        };
      }

      if (index === amountColumn) {
        column.sort = {
          compare: (left, right) => Number(left) - Number(right),
        };
        column.formatter = formatMoney;
      }

      return column;
    });
    const data = rows.map((row) => Array.from(row.cells, (cell, index) => {
      if (hasActions && index === 0) return row.dataset.id || '';
      return cell.dataset.order || cell.textContent.trim();
    }));

    const mount = document.createElement('div');
    mount.className = 'gridjs-record-table';
    table.before(mount);

    new gridjs.Grid({
      columns,
      data,
      search: true,
      sort: true,
      pagination: { limit: 25 },
      language,
      style: tableCellStyles,
    }).render(mount);
    table.hidden = true;
  });

  document.querySelectorAll('.summary-table').forEach((table) => {
    const headers = Array.from(table.querySelectorAll('thead th'));
    const plannedAverageColumn = headers.findIndex(
      (cell) => cell.textContent.trim() === 'Среднее план'
    );
    const categoryColumnWidth = headers.length > 1 ? 15 : 100;
    const valueColumnWidth = headers.length > 1
      ? (100 - categoryColumnWidth) / (headers.length - 1)
      : 0;
    const columns = headers.map((cell, index) => {
      const name = cell.textContent.trim();
      if (index === plannedAverageColumn) {
        return {
          name,
          width: `${valueColumnWidth}%`,
          formatter: (value) => formatMoney(
            value && typeof value === 'object' ? value.value : value
          ),
        };
      }

      return {
        name,
        width: `${index === 0 ? categoryColumnWidth : valueColumnWidth}%`,
        ...(index === 0 ? {} : { formatter: formatMoney }),
      };
    });
    const data = Array.from(table.querySelectorAll('tbody tr, tfoot tr'), (row) =>
      Array.from(row.cells, (cell, index) => {
        if (
          index === plannedAverageColumn
          && cell.classList.contains('planned-average')
        ) {
          return {
            categoryType: cell.dataset.categoryType,
            categoryId: cell.dataset.categoryId,
            value: cell.dataset.value,
          };
        }
        return cell.dataset.order || cell.textContent.trim();
      })
    );
    const mount = document.createElement('div');
    mount.className = 'gridjs-summary-table';
    const grid = new gridjs.Grid({
      columns,
      data,
      search: false,
      sort: false,
      pagination: false,
      language,
      style: tableCellStyles,
    });

    if (plannedAverageColumn !== -1) {
      mount.classList.add('has-planned-average');
      grid.config.eventEmitter.on('cellClick', (event, cell, column) => {
        if (
          column.name !== 'Среднее план'
          || !cell.data
          || !cell.data.categoryId
        ) {
          return;
        }

        const tableCell = event.currentTarget;
        if (tableCell.querySelector('.planned-average-input')) {
          return;
        }

        const input = document.createElement('input');
        input.type = 'number';
        input.step = '0.01';
        input.className = 'form-control planned-average-input';
        input.dataset.categoryType = cell.data.categoryType;
        input.dataset.categoryId = cell.data.categoryId;
        input.dataset.originalValue = cell.data.value || '';
        input.value = cell.data.value || '';
        tableCell.textContent = '';
        tableCell.append(input);
        input.focus();
      });
    }

    table.before(mount);
    grid.render(mount);
    table.hidden = true;
  });
});

document.addEventListener('click', async (event) => {
  const deleteLink = event.target.closest('.gridjs-delete-icon');
  if (!deleteLink) return;

  event.preventDefault();
  if (!window.confirm('Вы действительно хотите удалить эту запись?')) return;

  const token = document.querySelector('#token input')?.value;
  if (!token) {
    window.alert('Не удалось получить CSRF-токен. Обновите страницу и попробуйте снова.');
    return;
  }

  deleteLink.style.pointerEvents = 'none';
  try {
    const response = await fetch(deleteLink.dataset.deleteUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': token,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      deleteLink.style.pointerEvents = '';
      window.alert('Ошибка при удалении записи');
      return;
    }

    window.location.reload();
  } catch (error) {
    console.error('Не удалось удалить запись:', error);
    deleteLink.style.pointerEvents = '';
    window.alert('Не удалось связаться с сервером. Проверьте соединение и попробуйте снова.');
  }
});
