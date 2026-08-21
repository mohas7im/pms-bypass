document.addEventListener('DOMContentLoaded', () => {
    // CSRF Token Helper
    function getCsrfToken() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input) return input.value;
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    // State Variables
    let currentStep = 1;
    let selectedFile = null;
    let previewRecords = [];
    let cachedStatuses = [];

    // DOM Elements
    const alertBanner = document.getElementById('alert-banner');
    
    // Wizard steps
    const step1Card = document.getElementById('step-1-card');
    const step2Card = document.getElementById('step-2-card');
    const step3Card = document.getElementById('step-3-card');
    const stepNav1 = document.getElementById('step-nav-1');
    const stepNav2 = document.getElementById('step-nav-2');
    const stepNav3 = document.getElementById('step-nav-3');

    // Step 1 Elements
    const connectionForm = document.getElementById('connection-form');
    const openprojectUrlInput = document.getElementById('openproject-url');
    const apiTokenInput = document.getElementById('api-token');
    const btnConnect = document.getElementById('btn-connect');
    const connectSpinner = document.getElementById('connect-spinner');
    const btnDisconnect = document.getElementById('btn-disconnect');
    const headerStatus = document.getElementById('header-status');

    // Step 2 Elements
    const selectProject = document.getElementById('select-project');
    const selectType = document.getElementById('select-type');
    const selectStatus = document.getElementById('select-status');
    const selectAssignee = document.getElementById('select-assignee');
    const selectAccountable = document.getElementById('select-accountable');
    const btnBackStep1 = document.getElementById('btn-back-step-1');
    const btnContinueStep2 = document.getElementById('btn-continue-step-2');

    // Step 3 Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const fileNameText = document.getElementById('file-name-text');
    const btnClearFile = document.getElementById('btn-clear-file');
    
    const previewContainer = document.getElementById('preview-container');
    const previewTbody = document.getElementById('preview-tbody');
    const statTotalTasks = document.getElementById('stat-total-tasks');
    const statTotalHours = document.getElementById('stat-total-hours');
    const statDuplicateBadge = document.getElementById('stat-duplicate-badge');
    const statDuplicates = document.getElementById('stat-duplicates');

    const btnBackStep2 = document.getElementById('btn-back-step-2');
    const btnRunImport = document.getElementById('btn-run-import');
    const importSpinner = document.getElementById('import-spinner');

    // Result Modal Elements
    const resultModal = document.getElementById('result-modal');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const btnDoneModal = document.getElementById('btn-done-modal');
    const resWpCount = document.getElementById('res-wp-count');
    const resTeCount = document.getElementById('res-te-count');
    const resSkippedCount = document.getElementById('res-skipped-count');
    const resFailedCount = document.getElementById('res-failed-count');
    const resTotalHours = document.getElementById('res-total-hours');
    const resLogPath = document.getElementById('res-log-path');
    const resultTbody = document.getElementById('result-tbody');

    // Helper: Show Alert
    function showAlert(message, type = 'error') {
        alertBanner.textContent = message;
        alertBanner.className = `alert-banner ${type}`;
        alertBanner.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function hideAlert() {
        alertBanner.classList.add('hidden');
        alertBanner.textContent = '';
    }

    // Step Switcher
    function goToStep(step) {
        hideAlert();
        currentStep = step;

        step1Card.classList.toggle('hidden', step !== 1);
        step2Card.classList.toggle('hidden', step !== 2);
        step3Card.classList.toggle('hidden', step !== 3);

        stepNav1.classList.toggle('active', step >= 1);
        stepNav2.classList.toggle('active', step >= 2);
        stepNav3.classList.toggle('active', step >= 3);
    }

    // STEP 1: Connect Form Handler
    connectionForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideAlert();

        const url = openprojectUrlInput.value.trim();
        const token = apiTokenInput.value.trim();

        if (!url || !token) {
            showAlert('Please provide both OpenProject URL and API token.');
            return;
        }

        btnConnect.disabled = true;
        connectSpinner.classList.remove('hidden');

        try {
            const resp = await fetch('/api/test-connection/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ url, token })
            });

            const data = await resp.json();

            if (!data.success) {
                showAlert(data.error || 'Unable to connect to OpenProject.');
                return;
            }

            // Update Header Status
            headerStatus.innerHTML = `
                <span class="status-indicator active retro-glow-green"></span>
                <span class="status-text retro-font">USER: <strong>${data.user.name || 'User'}</strong></span>
                <button class="btn btn-secondary btn-sm retro-btn" id="btn-disconnect-dynamic">[ DISCONNECT ]</button>
            `;

            // Populate Projects Select with Hierarchy Grouping
            populateProjectDropdown(selectProject, data.projects);

            showAlert(`Connected successfully as ${data.user.name}!`, 'success');
            setTimeout(() => {
                hideAlert();
                goToStep(2);
            }, 1000);

        } catch (err) {
            showAlert(`Connection error: ${err.message}`);
        } finally {
            btnConnect.disabled = false;
            connectSpinner.classList.add('hidden');
        }
    });

    // STEP 2: Project Selection Change
    selectProject.addEventListener('change', async () => {
        const projectId = selectProject.value;
        if (!projectId) {
            selectType.innerHTML = '<option value="">-- Default (Task) --</option>';
            selectStatus.innerHTML = '<option value="">-- Default --</option>';
            if (selectAssignee) selectAssignee.innerHTML = '<option value="">-- UNASSIGNED (NONE) --</option>';
            if (selectAccountable) selectAccountable.innerHTML = '<option value="">-- UNASSIGNED (NONE) --</option>';
            return;
        }

        selectType.innerHTML = '<option value="">⏳ Loading types...</option>';
        selectStatus.innerHTML = '<option value="">⏳ Loading statuses...</option>';
        if (selectAssignee) selectAssignee.innerHTML = '<option value="">⏳ Loading users...</option>';
        if (selectAccountable) selectAccountable.innerHTML = '<option value="">⏳ Loading users...</option>';

        try {
            const resp = await fetch('/api/project-details/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ project_id: projectId })
            });

            const data = await resp.json();
            if (data.success) {
                cachedStatuses = data.statuses || [];

                // Populate Types
                selectType.innerHTML = '<option value="">-- Default (Task) --</option>';
                if (data.types && data.types.length > 0) {
                    data.types.forEach(t => {
                        const opt = document.createElement('option');
                        opt.value = t.id;
                        opt.textContent = t.name;
                        if (t.is_default || t.name.toLowerCase() === 'task') opt.selected = true;
                        selectType.appendChild(opt);
                    });
                }

                // Populate Statuses
                selectStatus.innerHTML = '<option value="">-- Select Status --</option>';
                const singleStatus = document.getElementById('single-status');
                if (singleStatus) singleStatus.innerHTML = '<option value="">-- DEFAULT (FROM STAGE 2) --</option>';

                if (data.statuses && data.statuses.length > 0) {
                    data.statuses.forEach(s => {
                        const opt = document.createElement('option');
                        opt.value = s.id;
                        opt.textContent = s.name + (s.is_closed ? ' (Closed)' : '');
                        if (s.name.toLowerCase() === 'in progress' || s.is_default) {
                            opt.selected = true;
                        }
                        selectStatus.appendChild(opt);

                        if (singleStatus) {
                            const optSingle = document.createElement('option');
                            optSingle.value = s.name;
                            optSingle.textContent = s.name;
                            singleStatus.appendChild(optSingle);
                        }
                    });
                }

                // Populate Assignees and Accountables
                if (selectAssignee && selectAccountable) {
                    selectAssignee.innerHTML = '<option value="">-- UNASSIGNED (NONE) --</option>';
                    selectAccountable.innerHTML = '<option value="">-- UNASSIGNED (NONE) --</option>';

                    if (data.users && data.users.length > 0) {
                        data.users.forEach(u => {
                            const optAss = document.createElement('option');
                            optAss.value = u.id;
                            optAss.textContent = u.name + (u.email ? ` (${u.email})` : '');
                            selectAssignee.appendChild(optAss);

                            const optAcc = document.createElement('option');
                            optAcc.value = u.id;
                            optAcc.textContent = u.name + (u.email ? ` (${u.email})` : '');
                            selectAccountable.appendChild(optAcc);
                        });
                    }
                }

                // Populate Existing OpenProject Tasks Autocomplete
                const recentTitlesDatalist = document.getElementById('recent-titles-list');
                if (data.existing_tasks && data.existing_tasks.length > 0) {
                    if (!window._recentTitles) window._recentTitles = new Set();
                    data.existing_tasks.forEach(wp => {
                        if (wp.subject) window._recentTitles.add(wp.subject);
                    });
                    if (recentTitlesDatalist) {
                        recentTitlesDatalist.innerHTML = Array.from(window._recentTitles)
                            .map(t => `<option value="${escapeHtml(t)}"></option>`)
                            .join('');
                    }
                }
            } else {
                showAlert('Could not load project details: ' + (data.error || 'Unknown error'));
                selectType.innerHTML = '<option value="">-- Default (Task) --</option>';
                selectStatus.innerHTML = '<option value="">-- Default --</option>';
            }
        } catch (err) {
            console.error('Failed to fetch project details:', err);
            selectType.innerHTML = '<option value="">-- Default (Task) --</option>';
            selectStatus.innerHTML = '<option value="">-- Default --</option>';
        }
    });

    btnBackStep1.addEventListener('click', () => goToStep(1));

    btnContinueStep2.addEventListener('click', () => {
        if (!selectProject.value) {
            showAlert('Please select a project before continuing.');
            return;
        }
        hideAlert();
        goToStep(3);
    });

    // STEP 3: File Upload, Direct JSON Text Input & Single Task Entry
    const tabBtnFile = document.getElementById('tab-btn-file');
    const tabBtnJson = document.getElementById('tab-btn-json');
    const tabBtnSingle = document.getElementById('tab-btn-single');

    const tabContentFile = document.getElementById('tab-content-file');
    const tabContentJson = document.getElementById('tab-content-json');
    const tabContentSingle = document.getElementById('tab-content-single');

    const jsonTextArea = document.getElementById('json-text-area');
    const btnPreviewJsonText = document.getElementById('btn-preview-json-text');

    const singleEntryForm = document.getElementById('single-entry-form');
    const singleDateInput = document.getElementById('single-date');
    const singleTitleInput = document.getElementById('single-title');
    const singleDescriptionInput = document.getElementById('single-description');
    const singleHoursInput = document.getElementById('single-hours');

    // Default single entry date to today (YYYY-MM-DD)
    if (singleDateInput) {
        const today = new Date().toISOString().split('T')[0];
        singleDateInput.value = today;
    }

    if (tabBtnJson && tabBtnSingle) {
        tabBtnSingle.addEventListener('click', () => {
            tabBtnSingle.classList.add('active');
            tabBtnJson.classList.remove('active');

            if (tabContentSingle) tabContentSingle.classList.remove('hidden');
            if (tabContentJson) tabContentJson.classList.add('hidden');
        });

        tabBtnJson.addEventListener('click', () => {
            tabBtnJson.classList.add('active');
            tabBtnSingle.classList.remove('active');

            if (tabContentJson) tabContentJson.classList.remove('hidden');
            if (tabContentSingle) tabContentSingle.classList.add('hidden');
        });
    }

    if (btnPreviewJsonText) {
        btnPreviewJsonText.addEventListener('click', (e) => {
            e.preventDefault();
            const rawJson = jsonTextArea.value.trim();
            if (!rawJson) {
                showAlert('Please paste valid JSON array content into the text area.');
                return;
            }
            selectedFile = null;
            handlePastedJson(rawJson);
        });
    }

    if (singleEntryForm) {
        singleEntryForm.addEventListener('submit', (e) => {
            e.preventDefault();
            hideAlert();

            const dateVal = singleDateInput.value.trim();
            const titleVal = singleTitleInput.value.trim();
            const descVal = singleDescriptionInput ? singleDescriptionInput.value.trim() : '';
            const hoursVal = singleHoursInput ? parseFloat(singleHoursInput.value) : 0;

            const singleStatusInput = document.getElementById('single-status');
            const chkKeepTitle = document.getElementById('chk-keep-title');
            const recentTitlesDatalist = document.getElementById('recent-titles-list');
            const statusVal = singleStatusInput ? singleStatusInput.value.trim() : '';

            if (!dateVal || !titleVal) {
                showAlert('Please provide both a valid Date and Task Title.');
                return;
            }

            // Save to recent titles set & update datalist
            if (titleVal && recentTitlesDatalist) {
                if (!window._recentTitles) window._recentTitles = new Set();
                window._recentTitles.add(titleVal);
                recentTitlesDatalist.innerHTML = Array.from(window._recentTitles)
                    .map(t => `<option value="${escapeHtml(t)}"></option>`)
                    .join('');
            }

            const recordObj = [{
                date: dateVal,
                title: titleVal,
                description: descVal,
                hours: isNaN(hoursVal) ? 0 : hoursVal,
                status: statusVal || null
            }];

            selectedFile = null;
            handlePastedJson(JSON.stringify(recordObj));

            // If keep title is checked, keep title input filled for quick status/entry change
            if (chkKeepTitle && chkKeepTitle.checked) {
                singleTitleInput.value = titleVal;
            }
        });
    }

    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                handleFileSelected(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files && fileInput.files.length > 0) {
                handleFileSelected(fileInput.files[0]);
            }
        });

        if (btnClearFile) {
            btnClearFile.addEventListener('click', (e) => {
                e.stopPropagation();
                fileInput.value = '';
                selectedFile = null;
                if (fileInfo) fileInfo.classList.add('hidden');
                previewContainer.classList.add('hidden');
            });
        }
    }

    async function handlePastedJson(rawJsonText) {
        hideAlert();
        const formData = new FormData();
        formData.append('json_text', rawJsonText);
        formData.append('project_id', selectProject.value);

        await processPreviewFormData(formData);
    }

    async function handleFileSelected(file) {
        selectedFile = file;
        fileNameText.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        fileInfo.classList.remove('hidden');
        hideAlert();

        const formData = new FormData();
        formData.append('file', file);
        formData.append('project_id', selectProject.value);

        await processPreviewFormData(formData);
    }

    async function processPreviewFormData(formData) {
        try {
            const resp = await fetch('/api/upload-preview/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken()
                },
                body: formData
            });

            const data = await resp.json();

            if (!data.success) {
                const errs = (data.errors || []).join('<br>');
                showAlert(errs || 'Failed to parse input data.');
                previewContainer.classList.add('hidden');
                return;
            }

            // Render Preview
            previewRecords = data.records || [];
            statTotalTasks.textContent = data.total_tasks;
            statTotalHours.textContent = data.total_hours;

            if (data.duplicate_count > 0) {
                statDuplicates.textContent = data.duplicate_count;
                statDuplicateBadge.classList.remove('hidden');
            } else {
                statDuplicateBadge.classList.add('hidden');
            }

            renderPreviewTable(previewRecords);
            previewContainer.classList.remove('hidden');

            if (data.errors && data.errors.length > 0) {
                showAlert(`Warnings during parsing:<br>${data.errors.join('<br>')}`, 'error');
            }

        } catch (err) {
            showAlert(`Parsing error: ${err.message}`);
        }
    }

    function renderPreviewTable(records) {
        previewTbody.innerHTML = '';
        records.forEach((rec, idx) => {
            const tr = document.createElement('tr');
            if (rec.is_duplicate) {
                tr.classList.add('row-duplicate');
            }

            const currentStatus = rec.status || (selectStatus ? selectStatus.value : '');
            let statusOptionsHtml = '<option value="">Default (Stage 2)</option>';
            if (cachedStatuses && cachedStatuses.length > 0) {
                statusOptionsHtml = cachedStatuses.map(s => {
                    const isSel = (rec.status && (rec.status.toString().toLowerCase() === s.name.toLowerCase() || rec.status.toString() === s.id.toString()))
                        || (!rec.status && selectStatus.value && selectStatus.value.toString() === s.id.toString());
                    return `<option value="${s.id}" ${isSel ? 'selected' : ''}>${s.name}</option>`;
                }).join('');
            }

            tr.innerHTML = `
                <td>${idx + 1}</td>
                <td><strong>${rec.date}</strong></td>
                <td>${escapeHtml(rec.title)}</td>
                <td>${escapeHtml(rec.description || '-')}</td>
                <td>${rec.hours ? rec.hours + ' hrs' : '-'}</td>
                <td>
                    <select class="form-control retro-input row-status-select" data-idx="${idx}" style="padding: 2px 6px; font-size: 0.85rem; height: auto;">
                        ${statusOptionsHtml}
                    </select>
                </td>
                <td>
                    ${rec.is_duplicate 
                        ? `<span class="tag-dup">Duplicate (WP #${rec.existing_wp_id})</span>` 
                        : `<span class="tag-new">New Entry</span>`}
                </td>
            `;
            previewTbody.appendChild(tr);
        });
    }

    // Attach event delegation for row status change
    previewTbody.addEventListener('change', (e) => {
        if (e.target && e.target.classList.contains('row-status-select')) {
            const idx = parseInt(e.target.dataset.idx, 10);
            if (!isNaN(idx) && previewRecords[idx]) {
                previewRecords[idx].status = e.target.value;
            }
        }
    });

    const btnBackStep2Preview = document.getElementById('btn-back-step-2-preview');
    if (btnBackStep2) btnBackStep2.addEventListener('click', () => goToStep(2));
    if (btnBackStep2Preview) btnBackStep2Preview.addEventListener('click', () => goToStep(2));

    // Execute Import Handler
    btnRunImport.addEventListener('click', async () => {
        if (!previewRecords || previewRecords.length === 0) {
            showAlert('No valid records to import.');
            return;
        }

        hideAlert();
        btnRunImport.disabled = true;
        importSpinner.classList.remove('hidden');

        try {
            const payload = {
                project_id: selectProject.value,
                type_id: selectType.value || null,
                status_id: selectStatus.value || null,
                assignee_id: selectAssignee ? selectAssignee.value || null : null,
                accountable_id: selectAccountable ? selectAccountable.value || null : null,
                records: previewRecords
            };

            const resp = await fetch('/api/execute-import/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(payload)
            });

            const data = await resp.json();

            if (!data.success) {
                showAlert(data.error || 'Import failed to complete.');
                return;
            }

            const res = data.results;
            resWpCount.textContent = res.created_work_packages;
            resTeCount.textContent = res.created_time_entries;
            resSkippedCount.textContent = res.skipped_duplicates;
            resFailedCount.textContent = res.failed_count;
            resTotalHours.textContent = res.total_hours;
            resLogPath.textContent = res.log_file || 'logs/import.log';

            renderResultDetailsTable(res.records_details || []);
            resultModal.classList.remove('hidden');

        } catch (err) {
            showAlert(`Import execution error: ${err.message}`);
        } finally {
            btnRunImport.disabled = false;
            importSpinner.classList.add('hidden');
        }
    });

    function renderResultDetailsTable(details) {
        resultTbody.innerHTML = '';
        details.forEach(d => {
            const tr = document.createElement('tr');
            let statusBadge = '';
            if (d.status === 'SUCCESS') {
                statusBadge = '<span class="tag-new">Created</span>';
            } else if (d.status === 'SKIPPED') {
                statusBadge = '<span class="tag-dup">Skipped</span>';
            } else {
                statusBadge = '<span class="badge" style="background:rgba(239, 68, 68, 0.2);color:#fca5a5;">Failed</span>';
            }

            tr.innerHTML = `
                <td>${d.date}</td>
                <td>${escapeHtml(d.title)}</td>
                <td>${d.hours ? d.hours + ' hrs' : '-'}</td>
                <td>${statusBadge}</td>
                <td>${escapeHtml(d.reason || (d.wp_created ? `Created WP #${d.wp_id}` : 'OK'))}</td>
            `;
            resultTbody.appendChild(tr);
        });
    }

    // Modal Close Handlers
    function closeModal() {
        resultModal.classList.add('hidden');
    }
    btnCloseModal.addEventListener('click', closeModal);
    btnDoneModal.addEventListener('click', closeModal);

    // Disclaimer Modal Handlers
    const disclaimerModal = document.getElementById('disclaimer-modal');
    const chkAcceptDisclaimer = document.getElementById('chk-accept-disclaimer');
    const btnAcceptDisclaimer = document.getElementById('btn-accept-disclaimer');
    const btnCloseDisclaimer = document.getElementById('btn-close-disclaimer');
    const btnShowDisclaimer = document.getElementById('btn-show-disclaimer');

    if (disclaimerModal) {
        // Show disclaimer on home page if not yet accepted (one time only)
        if (localStorage.getItem('disclaimer_accepted') !== 'true') {
            disclaimerModal.classList.remove('hidden');
        }

        if (chkAcceptDisclaimer && btnAcceptDisclaimer) {
            chkAcceptDisclaimer.addEventListener('change', () => {
                if (chkAcceptDisclaimer.checked) {
                    btnAcceptDisclaimer.disabled = false;
                    btnAcceptDisclaimer.style.opacity = '1';
                    btnAcceptDisclaimer.style.cursor = 'pointer';
                } else {
                    btnAcceptDisclaimer.disabled = true;
                    btnAcceptDisclaimer.style.opacity = '0.5';
                    btnAcceptDisclaimer.style.cursor = 'not-allowed';
                }
            });
        }

        const closeDisclaimer = () => {
            if (chkAcceptDisclaimer && !chkAcceptDisclaimer.checked) return;
            localStorage.setItem('disclaimer_accepted', 'true');
            disclaimerModal.classList.add('hidden');
        };

        if (btnAcceptDisclaimer) btnAcceptDisclaimer.addEventListener('click', closeDisclaimer);
        if (btnCloseDisclaimer) {
            btnCloseDisclaimer.addEventListener('click', () => {
                disclaimerModal.classList.add('hidden');
            });
        }
        if (btnShowDisclaimer) {
            btnShowDisclaimer.addEventListener('click', () => {
                disclaimerModal.classList.remove('hidden');
            });
        }
    }

    // Disconnect Handler & State Reset
    function resetConnectionState() {
        if (headerStatus) {
            headerStatus.innerHTML = `
                <span class="status-indicator inactive retro-glow-red"></span>
                <span class="status-text retro-font">[ NOT CONNECTED ]</span>
            `;
        }
        if (apiTokenInput) apiTokenInput.value = '';
        if (selectProject) selectProject.innerHTML = '<option value="">-- SELECT OPENPROJECT PROJECT --</option>';
        if (selectType) selectType.innerHTML = '<option value="">-- DEFAULT (TASK) --</option>';
        if (selectStatus) selectStatus.innerHTML = '<option value="">-- DEFAULT --</option>';
        if (selectAssignee) selectAssignee.innerHTML = '<option value="">-- UNASSIGNED (NONE) --</option>';
        if (selectAccountable) selectAccountable.innerHTML = '<option value="">-- UNASSIGNED (NONE) --</option>';
        if (previewContainer) previewContainer.classList.add('hidden');
        goToStep(1);
    }

    function attachDisconnectHandler() {
        document.body.addEventListener('click', async (e) => {
            const btn = e.target.closest('#btn-disconnect, #btn-disconnect-dynamic');
            if (btn) {
                e.preventDefault();
                try {
                    await fetch('/api/disconnect/', {
                        method: 'POST',
                        headers: { 'X-CSRFToken': getCsrfToken() }
                    });
                } catch (err) {
                    console.error('Disconnect API call failed:', err);
                }
                resetConnectionState();
                showAlert('Disconnected from OpenProject session.', 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 400);
            }
        });
    }
    attachDisconnectHandler();
    function populateProjectDropdown(selectElem, projects) {
        selectElem.innerHTML = '<option value="">-- SELECT OPENPROJECT PROJECT --</option>';
        if (!projects || projects.length === 0) return;

        const projectMap = {};
        const roots = [];
        const orphanChildren = {};

        projects.forEach(p => {
            projectMap[p.id] = { ...p, children: [] };
        });

        projects.forEach(p => {
            const item = projectMap[p.id];
            if (p.parent_id && projectMap[p.parent_id]) {
                projectMap[p.parent_id].children.push(item);
            } else if (p.parent_id && !projectMap[p.parent_id]) {
                const pGroup = p.parent_name || `Parent Project #${p.parent_id}`;
                if (!orphanChildren[pGroup]) orphanChildren[pGroup] = [];
                orphanChildren[pGroup].push(item);
            } else {
                roots.push(item);
            }
        });

        function appendChildOptions(container, items, level = 1) {
            items.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id;
                const indent = ' '.repeat((level - 1) * 3) + '└── ';
                opt.textContent = `${indent}${item.name} (${item.identifier})`;
                container.appendChild(opt);

                if (item.children && item.children.length > 0) {
                    appendChildOptions(container, item.children, level + 1);
                }
            });
        }

        // Render Roots & Groups
        roots.forEach(root => {
            if (root.children && root.children.length > 0) {
                const group = document.createElement('optgroup');
                group.label = `📁 ${root.name.toUpperCase()}`;

                // Parent option itself
                const parentOpt = document.createElement('option');
                parentOpt.value = root.id;
                parentOpt.textContent = `📁 ${root.name} [Main Space] (${root.identifier})`;
                group.appendChild(parentOpt);

                appendChildOptions(group, root.children, 1);
                selectElem.appendChild(group);
            } else {
                const opt = document.createElement('option');
                opt.value = root.id;
                opt.textContent = `📄 ${root.name} (${root.identifier})`;
                selectElem.appendChild(opt);
            }
        });

        // Render Orphan Sub-projects
        Object.keys(orphanChildren).forEach(groupName => {
            const group = document.createElement('optgroup');
            group.label = `📁 ${groupName.toUpperCase()}`;
            appendChildOptions(group, orphanChildren[groupName], 1);
            selectElem.appendChild(group);
        });

        if (projects.length === 1) {
            selectElem.value = projects[0].id;
            selectElem.dispatchEvent(new Event('change'));
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
});
