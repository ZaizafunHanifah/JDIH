const API_BASE = '/api';

let state = {
    view: 'years',
    q: '',
    topic: null,
    jenis: '',
    tahun: '',
    sort: 'terbaru',
    page: 1,
    limit: 10,
};

let debounceTimer = null;
let yearFetchVersion = 0;
let currentAbortController = null;

const searchInput = document.getElementById('searchInput');
const jenisFilter = document.getElementById('jenisFilter');
const topicChipsContainer = document.getElementById('topicChips');
const yearGrid = document.getElementById('yearGrid');
const yearsHeading = document.getElementById('yearsHeading');
const stateYears = document.getElementById('stateYears');
const stateTable = document.getElementById('stateTable');
const breadcrumbBack = document.getElementById('breadcrumbBack');
const breadcrumbText = document.getElementById('breadcrumbText');
const docTableBody = document.getElementById('docTableBody');
const pagination = document.getElementById('pagination');
const showingCount = document.getElementById('showingCount');
const totalCount = document.getElementById('totalCount');
const tableMeta = document.getElementById('tableMeta');
const resetBtn = document.getElementById('resetFilters');

async function fetchTopics() {
    try {
        const res = await fetch(`${API_BASE}/topics`);
        if (!res.ok) throw new Error('Gagal memuat topik');
        return await res.json();
    } catch (err) {
        console.error('fetchTopics error:', err);
        return [];
    }
}

async function fetchJenisDokumen() {
    try {
        const res = await fetch(`${API_BASE}/jenis-dokumen`);
        if (!res.ok) throw new Error('Gagal memuat jenis dokumen');
        return await res.json();
    } catch (err) {
        console.error('fetchJenisDokumen error:', err);
        return [];
    }
}

async function fetchDocuments(params = {}) {
    if (currentAbortController) {
        currentAbortController.abort();
    }
    currentAbortController = new AbortController();

    const searchParams = new URLSearchParams();
    if (state.q) searchParams.set('q', state.q);
    if (state.topic) searchParams.set('topic', state.topic);
    if (state.jenis) searchParams.set('jenis', state.jenis);
    if (state.tahun) searchParams.set('tahun', state.tahun);
    searchParams.set('sort', state.sort);
    searchParams.set('page', state.page);
    searchParams.set('limit', state.limit);

    Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
            searchParams.set(k, v);
        }
    });

    try {
        const res = await fetch(`${API_BASE}/documents?${searchParams.toString()}`, {
            signal: currentAbortController.signal
        });
        if (!res.ok) throw new Error('Gagal memuat dokumen');
        return await res.json();
    } catch (err) {
        if (err.name === 'AbortError') {
            return { data: [], pagination: { total: 0, page: 1, total_pages: 1 }, aborted: true };
        }
        console.error('fetchDocuments error:', err);
        return { data: [], pagination: { total: 0, page: 1, total_pages: 1 } };
    }
}

async function fetchYearCount(tahun, jenis, topic) {
    const params = new URLSearchParams();
    params.set('tahun', tahun);
    params.set('limit', '1');
    if (jenis) params.set('jenis', jenis);
    if (topic) params.set('topic', topic);

    try {
        const res = await fetch(`${API_BASE}/documents?${params.toString()}`);
        if (!res.ok) return { tahun, total: 0 };
        const data = await res.json();
        return { tahun, total: data.pagination?.total || 0 };
    } catch (err) {
        console.error(`fetchYearCount error for ${tahun}:`, err);
        return { tahun, total: 0 };
    }
}

async function fetchYearCounts() {
    yearFetchVersion++;
    const currentVersion = yearFetchVersion;

    const years = Array.from({ length: 16 }, (_, i) => 2011 + i);
    const promises = years.map(tahun => fetchYearCount(tahun, state.jenis, state.topic));

    const results = await Promise.all(promises);

    if (currentVersion !== yearFetchVersion) {
        return null;
    }

    return results;
}

function renderJenisOptions(jenisList) {
    const defaultJenis = 'Peraturan Bupati';
    let hasDefault = false;

    jenisFilter.innerHTML = '<option value="">Semua Jenis</option>';
    jenisList.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.jenis;
        opt.textContent = `${item.jenis} (${item.jumlah})`;
        if (item.jenis === defaultJenis) hasDefault = true;
        jenisFilter.appendChild(opt);
    });

    if (hasDefault && !state.jenis) {
        jenisFilter.value = defaultJenis;
        state.jenis = defaultJenis;
    }
}

function renderTopics(topics, activeTopicId = null) {
    topicChipsContainer.innerHTML = '';
    topics.forEach(topic => {
        const btn = document.createElement('button');
        btn.className = `topic-chip${topic.id === activeTopicId ? ' active' : ''}`;
        btn.dataset.topicId = topic.id;
        btn.innerHTML = `${topic.label_topik} <span class="count">${topic.jumlah_dokumen}</span>`;
        btn.addEventListener('click', () => toggleTopic(topic.id));
        topicChipsContainer.appendChild(btn);
    });
}

function updateTopicChipsActive() {
    document.querySelectorAll('.topic-chip').forEach(chip => {
        const id = parseInt(chip.dataset.topicId, 10);
        chip.classList.toggle('active', id === state.topic);
    });
}

function toggleTopic(topicId) {
    if (state.topic === topicId) {
        state.topic = null;
    } else {
        state.topic = topicId;
    }
    state.page = 1;
    updateTopicChipsActive();
    handleFilterChange();
}

function getJenisLabel() {
    const selected = jenisFilter.options[jenisFilter.selectedIndex];
    if (!selected || !selected.value) return 'SEMUA JENIS';
    return selected.textContent.split(' (')[0].toUpperCase();
}

async function renderYearGrid() {
    yearGrid.innerHTML = '<div class="loading" role="status" aria-live="polite"><div class="spinner" aria-hidden="true"></div>Memuat jumlah dokumen per tahun...</div>';

    const counts = await fetchYearCounts();
    if (!counts) return;

    const years = Array.from({ length: 16 }, (_, i) => 2011 + i);
    const countMap = new Map(counts.map(c => [c.tahun, c.total]));

    yearGrid.innerHTML = years.map(tahun => {
        const total = countMap.get(tahun) || 0;
        return `
            <article class="year-card" role="listitem" tabindex="0" data-tahun="${tahun}" aria-label="Tahun ${tahun}, ${total} dokumen">
                <div class="year-label">Tahun</div>
                <div class="year-value">${tahun}</div>
                <div class="year-count"><span class="num">${total.toLocaleString('id-ID')}</span> dokumen</div>
            </article>
        `;
    }).join('');

    yearGrid.querySelectorAll('.year-card').forEach(card => {
        card.addEventListener('click', () => onYearClick(parseInt(card.dataset.tahun, 10)));
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onYearClick(parseInt(card.dataset.tahun, 10));
            }
        });
    });
}

function onYearClick(tahun) {
    state.tahun = tahun;
    state.page = 1;
    switchToTableView();
    loadDocuments();
}

function switchToTableView() {
    state.view = 'table';
    stateYears.classList.add('hidden');
    stateTable.classList.remove('hidden');
    updateBreadcrumb();
    tableMeta.classList.remove('hidden');
}

function switchToYearsView() {
    state.view = 'years';
    stateYears.classList.remove('hidden');
    stateTable.classList.add('hidden');
    tableMeta.classList.add('hidden');
    renderYearGrid();
}

function updateBreadcrumb() {
    const hasSearchOrTopic = state.q || state.topic;
    const hasTahun = state.tahun;

    if (hasTahun && !hasSearchOrTopic) {
        breadcrumbText.textContent = '← Kembali ke Daftar Tahun';
        breadcrumbBack.onclick = (e) => {
            e.preventDefault();
            state.tahun = '';
            switchToYearsView();
        };
    } else {
        breadcrumbText.textContent = '← Reset dan Kembali';
        breadcrumbBack.onclick = (e) => {
            e.preventDefault();
            resetFilters();
        };
    }
}

function getJenisBadgeClass(jenis) {
    return 'badge-jenis';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' });
}

async function loadDocuments() {
    docTableBody.innerHTML = '<tr><td colspan="4"><div class="loading" role="status" aria-live="polite"><div class="spinner" aria-hidden="true"></div>Memuat dokumen...</div></td></tr>';

    const result = await fetchDocuments();
    if (result.aborted) return;
    renderDocumentTable(result.data, result.pagination);
}

function renderDocumentTable(data, paginationData) {
    if (!data || data.length === 0) {
        docTableBody.innerHTML = `
            <tr>
                <td colspan="4">
                    <div class="empty-state" role="status">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p>Tidak ada dokumen yang cocok</p>
                    </div>
                </td>
            </tr>
        `;
        showingCount.textContent = '0';
        totalCount.textContent = paginationData.total || 0;
        renderPagination(paginationData);
        return;
    }

    const startNum = (state.page - 1) * state.limit + 1;
    docTableBody.innerHTML = data.map((doc, idx) => {
        const topicsHtml = doc.topics.map(t => `<span class="badge badge-topic">${escapeHtml(t.label_topik)}</span>`).join('');
        const pdfUrl = doc.url_pdf || '#';
        const jenisBadge = `<span class="badge badge-jenis">${escapeHtml(doc.jenis_dokumen)}</span>`;
        const nomor = doc.nomor || '-';
        return `
            <tr>
                <td><span class="doc-number">${startNum + idx}</span></td>
                <td><span class="doc-date">${formatDate(doc.tanggal_terbit)}</span></td>
                <td>
                    <div class="doc-title-cell">${escapeHtml(doc.judul)}</div>
                    <div class="doc-badges">
                        ${jenisBadge}
                        ${topicsHtml}
                    </div>
                </td>
                <td style="text-align: center;">
                    <a href="${escapeHtml(pdfUrl)}" target="_blank" rel="noopener" class="btn-download">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                        Download
                    </a>
                </td>
            </tr>
        `;
    }).join('');

    showingCount.textContent = data.length;
    totalCount.textContent = paginationData.total || 0;
    renderPagination(paginationData);
}

function renderPagination(p) {
    const { page, total_pages } = p;
    if (total_pages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';
    html += `<button class="page-btn" ${page === 1 ? 'disabled' : ''} data-page="${page - 1}" aria-label="Halaman sebelumnya">‹ Sebelumnya</button>`;

    const maxVisible = 5;
    let start = Math.max(1, page - Math.floor(maxVisible / 2));
    let end = Math.min(total_pages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
        start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn${i === page ? ' active' : ''}" data-page="${i}" ${i === page ? 'aria-current="page"' : ''}>${i}</button>`;
    }

    html += `<button class="page-btn" ${page === total_pages ? 'disabled' : ''} data-page="${page + 1}" aria-label="Halaman selanjutnya">Selanjutnya ›</button>`;

    pagination.innerHTML = html;

    pagination.querySelectorAll('.page-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const pg = parseInt(btn.dataset.page, 10);
            if (!isNaN(pg) && pg !== page && pg >= 1 && pg <= total_pages) {
                state.page = pg;
                loadDocuments();
            }
        });
    });
}

function onSearchInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        state.q = searchInput.value.trim();
        state.page = 1;
        handleFilterChange();
    }, 300);
}

function onJenisChange() {
    state.jenis = jenisFilter.value;
    state.page = 1;
    if (state.view === 'years') {
        yearsHeading.textContent = `DAFTAR ${getJenisLabel()}`;
        renderYearGrid();
    } else {
        handleFilterChange();
    }
}

function handleFilterChange() {
    if (state.view === 'years' && (state.q || state.topic)) {
        switchToTableView();
    }
    loadDocuments();
    updateBreadcrumb();
}

function resetFilters() {
    state.q = '';
    state.topic = null;
    state.jenis = '';
    state.tahun = '';
    state.page = 1;
    searchInput.value = '';
    jenisFilter.value = 'Peraturan Bupati';
    state.jenis = 'Peraturan Bupati';
    updateTopicChipsActive();
    yearsHeading.textContent = `DAFTAR PERATURAN BUPATI`;
    switchToYearsView();
}

async function init() {
    const [topics, jenisList] = await Promise.all([
        fetchTopics(),
        fetchJenisDokumen()
    ]);
    renderTopics(topics);
    renderJenisOptions(jenisList);
    yearsHeading.textContent = `DAFTAR PERATURAN BUPATI`;
    await renderYearGrid();
}

searchInput.addEventListener('input', onSearchInput);
jenisFilter.addEventListener('change', onJenisChange);
resetBtn.addEventListener('click', resetFilters);

init();