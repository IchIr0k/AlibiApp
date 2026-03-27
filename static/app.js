document.addEventListener("DOMContentLoaded", function() {
  // Загрузка дополнительных квестов
  const loadBtn = document.getElementById("load-more");
  if (loadBtn) {
    loadBtn.addEventListener("click", async () => {
      const btn = loadBtn;
      let skip = parseInt(btn.dataset.skip || "0");

      // Получаем текущие параметры из URL
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
            // Получаем текущие ID квестов, чтобы не дублировать
            const existingIds = new Set();
            document.querySelectorAll('.card').forEach(card => {
              const link = card.querySelector('.btn-primary');
              if (link) {
                const href = link.getAttribute('href');
                const match = href.match(/\/quest\/(\d+)/);
                if (match) existingIds.add(parseInt(match[1]));
              }
            });

            // Получаем все новые карточки из ответа
            const newCards = newGrid.querySelectorAll('.card');
            let addedCount = 0;

            // Создаем массив для хранения новых карточек
            const cardsToAdd = [];

            newCards.forEach(newCard => {
              const link = newCard.querySelector('.btn-primary');
              if (link) {
                const href = link.getAttribute('href');
                const match = href.match(/\/quest\/(\d+)/);
                if (match) {
                  const questId = parseInt(match[1]);
                  if (!existingIds.has(questId)) {
                    cardsToAdd.push(newCard.cloneNode(true));
                    addedCount++;
                    existingIds.add(questId);
                  }
                }
              }
            });

            // Добавляем все новые карточки в конец
            cardsToAdd.forEach(card => {
              cardsGrid.appendChild(card);
            });

            // Обновляем skip на основе реально добавленных квестов
            const newSkip = skip + addedCount;
            btn.dataset.skip = newSkip;

            // Проверяем, сколько всего квестов на странице
            const totalCards = document.querySelectorAll('.card').length;

            // Если добавилось меньше 15 или всего квестов кратно 15, проверяем возможность загрузки еще
            if (addedCount < 15) {
              // Если добавилось меньше 15, значит больше нет квестов
              btn.style.display = 'none';
            } else {
              btn.textContent = "Посмотреть ещё";
              btn.disabled = false;
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

  // Применение фильтров
  const applyFilters = document.getElementById("apply-filters");
  if (applyFilters) {
    applyFilters.addEventListener("click", () => {
      const form = document.getElementById("filter-form");
      const data = new FormData(form);
      const params = new URLSearchParams();

      const genreValues = data.getAll("genre");
      const difficultyValues = data.getAll("difficulty");
      const fearLevel = data.get("fear_level");
      const players = data.get("players");

      genreValues.forEach(genre => {
        if (genre) params.append("genre", genre);
      });

      difficultyValues.forEach(difficulty => {
        if (difficulty) params.append("difficulty", difficulty);
      });

      if (fearLevel) params.append("fear_level", fearLevel);
      if (players) params.append("players", players);

      if (sortSelect && sortSelect.value) {
        params.append("sort", sortSelect.value);
      }

      window.location.href = "/?" + params.toString();
    });
  }

  // Инициализация фильтров из URL параметров
  function initFiltersFromURL() {
    const urlParams = new URLSearchParams(window.location.search);

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

    const genres = urlParams.getAll('genre');
    genres.forEach(genre => {
      const checkbox = document.querySelector(`input[name="genre"][value="${genre}"]`);
      if (checkbox) checkbox.checked = true;
    });

    const difficulties = urlParams.getAll('difficulty');
    difficulties.forEach(difficulty => {
      const checkbox = document.querySelector(`input[name="difficulty"][value="${difficulty}"]`);
      if (checkbox) checkbox.checked = true;
    });

    const sort = urlParams.get('sort');
    if (sort && sortSelect) {
      sortSelect.value = sort;
    }
  }

  initFiltersFromURL();
});