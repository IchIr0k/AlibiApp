document.addEventListener("DOMContentLoaded", function() {
  // Загрузка дополнительных квестов
  const loadBtn = document.getElementById("load-more");
  if (loadBtn) {
    loadBtn.addEventListener("click", async () => {
      const btn = loadBtn;
      const skip = parseInt(btn.dataset.skip || "0");
      const params = new URLSearchParams(window.location.search);
      params.set("skip", skip);

      const url = "/api/quests?" + params.toString();
      btn.disabled = true;
      btn.textContent = "Загрузка...";

      try {
        const res = await fetch(url);
        if (res.ok) {
          const html = await res.text();
          const tempDiv = document.createElement('div');
          tempDiv.innerHTML = html;
          const newGrid = tempDiv.querySelector('.cards-grid');

          const cardsGrid = document.querySelector(".cards-grid");
          if (newGrid && cardsGrid) {
            // Добавляем новые карточки
            const newCards = newGrid.innerHTML;
            cardsGrid.insertAdjacentHTML('beforeend', newCards);

            const addedCount = (newGrid.innerHTML.match(/class="card"/g) || []).length;
            const newSkip = skip + addedCount;
            btn.dataset.skip = newSkip;
            btn.textContent = "Посмотреть ещё";
            btn.disabled = false;

            // Скрываем кнопку если загружено меньше чем лимит
            if (addedCount === 0 || addedCount < 15) {
              btn.style.display = 'none';
            }
          } else {
            btn.textContent = "Нет данных";
            btn.disabled = true;
          }
        } else {
          btn.textContent = "Ошибка загрузки";
          btn.disabled = false;
        }
      } catch (error) {
        btn.textContent = "Ошибка";
        btn.disabled = false;
        console.error('Load more error:', error);
      }
    });
  }

  // Звезды рейтинга страха
  const fearStars = document.querySelectorAll("#fear-level span");
  const fearInput = document.getElementById("fear_input");

  if (fearStars.length) {
    fearStars.forEach(star => {
      star.addEventListener("click", () => {
        const value = parseInt(star.getAttribute("data-value"));
        fearInput.value = value;

        // Обновляем визуальное отображение
        fearStars.forEach((s, index) => {
          if (index < value) {
            s.classList.add("active");
            s.style.color = "gold";
            s.textContent = "★";
          } else {
            s.classList.remove("active");
            s.style.color = "gray";
            s.textContent = "☆";
          }
        });
      });
    });
  }

  // Выбор количества игроков
  const playerCircles = document.querySelectorAll("#players span");
  const playersInput = document.getElementById("players_input");

  if (playerCircles.length) {
    playerCircles.forEach(circle => {
      circle.addEventListener("click", () => {
        const value = parseInt(circle.getAttribute("data-value"));
        playersInput.value = value;

        // Обновляем визуальное отображение
        playerCircles.forEach((c, index) => {
          if (index < value) {
            c.classList.add("active");
            c.style.color = "#4CAF50";
            c.textContent = "●";
          } else {
            c.classList.remove("active");
            c.style.color = "gray";
            c.textContent = "○";
          }
        });
      });
    });
  }

  // Сортировка
  const sortSelect = document.getElementById('sort-select');
  if (sortSelect) {
    sortSelect.addEventListener('change', function() {
      const url = new URL(window.location);
      const params = new URLSearchParams(url.search);
      params.set('sort', this.value);
      window.location.href = "/?" + params.toString();
    });
  }

  // Применение фильтров - ИСПРАВЛЕНО
  const applyFilters = document.getElementById("apply-filters");
  if (applyFilters) {
    applyFilters.addEventListener("click", () => {
      const form = document.getElementById("filter-form");
      const data = new FormData(form);
      const params = new URLSearchParams();

      // Собираем все жанры
      const genreValues = data.getAll("genre");
      console.log("Selected genres:", genreValues);
      genreValues.forEach(genre => {
        if (genre) params.append("genre", genre);
      });

      // Собираем все сложности
      const difficultyValues = data.getAll("difficulty");
      console.log("Selected difficulties:", difficultyValues);
      difficultyValues.forEach(difficulty => {
        if (difficulty) params.append("difficulty", difficulty);
      });

      // Уровень страха
      const fearLevel = data.get("fear_level");
      if (fearLevel) params.append("fear_level", fearLevel);

      // Количество игроков
      const players = data.get("players");
      if (players) params.append("players", players);

      // Сортировка
      if (sortSelect && sortSelect.value) {
        params.append("sort", sortSelect.value);
      }

      console.log("Final URL params:", params.toString());
      window.location.href = "/?" + params.toString();
    });
  }

  // Инициализация фильтров из URL параметров
  function initFiltersFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    console.log("URL params:", urlParams.toString());

    // Уровень страха
    const fearLevel = urlParams.get('fear_level');
    if (fearLevel && fearInput) {
      fearInput.value = fearLevel;
      fearStars.forEach((star, index) => {
        if (index < fearLevel) {
          star.classList.add("active");
          star.style.color = "gold";
          star.textContent = "★";
        }
      });
    }

    // Количество игроков
    const players = urlParams.get('players');
    if (players && playersInput) {
      playersInput.value = players;
      playerCircles.forEach((circle, index) => {
        if (index < players) {
          circle.classList.add("active");
          circle.style.color = "#4CAF50";
          circle.textContent = "●";
        }
      });
    }

    // Чекбоксы жанров - получаем ВСЕ значения
    const genres = urlParams.getAll('genre');
    console.log("Genres from URL:", genres);
    genres.forEach(genre => {
      const checkbox = document.querySelector(`input[name="genre"][value="${genre}"]`);
      if (checkbox) checkbox.checked = true;
    });

    // Чекбоксы сложности - получаем ВСЕ значения
    const difficulties = urlParams.getAll('difficulty');
    console.log("Difficulties from URL:", difficulties);
    difficulties.forEach(difficulty => {
      const checkbox = document.querySelector(`input[name="difficulty"][value="${difficulty}"]`);
      if (checkbox) checkbox.checked = true;
    });

    // Сортировка
    const sort = urlParams.get('sort');
    if (sort && sortSelect) {
      sortSelect.value = sort;
    }
  }

  initFiltersFromURL();
});