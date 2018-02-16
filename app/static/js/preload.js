// *****************************************
// BANKPERSO PAGE DECLARATION: /preload.html
// -----------------------------------------
// Version: 1.0
// Date: 02-08-2016

LINE    = 'preload';
SUBLINE = 'article';

// ----------------------
// Dialog Action Handlers
// ----------------------

function $_reset_current_sort() {
    current_page = 1;
}

function $_next_current_sort() {
    current_sort = current_sort == LOG_SORT.length-1 ? 0 : current_sort + 1;
    $_reset_current_sort();
}

function $_deactivate_search() {
    is_search_activated = false;
    search_context = '';
    current_page = 1;
}

function $_reset_item() {
    refresh_current_state = true;
    SelectedReset();
}

function $_reset_page() {
    SelectedReset();
    current_row_id = null;
}

function $_calculating_disabled() {
    return false;
}

// --------------
// Page Functions
// --------------

function $Init() {
    SelectedReset();

    var parent = $("#line-content");
    var ob = $("tr[class~='selected']", parent);
    $onToggleSelectedClass(LINE, ob, 'add', null);

    var parent = $("#subline-content");
    var ob = $("tr[class~='selected']", parent);
    $onToggleSelectedClass(SUBLINE, ob, 'add', null);

    $ShowMenu('data-menu-articles');

    interrupt(true, 1);
}

function $Go(action) {
    $web_logging(action);
}

function $ShowOnStartup() {
    //$Go('401');
}

function $ActivateInfoData(show) {
    var container = $("#info-data");

    //alert('$ActivateInfoData:'+show);

    if (show)
        container.show();
    else
        container.hide();
}

function $ShowMenu(id) {
    //
    // Show (open) selected right side's Data menu item (Parameters/Products)
    //
    var articles = $("#subline-content");
    var preloadlog = $("#preloadline-content");

    if (selected_data_menu)
        selected_data_menu.removeClass('selected');

    selected_data_menu = $("#"+id);
    //$("#data-content").scrollTop(0);

    if (id == 'data-menu-articles') {
        articles.show();
        preloadlog.hide();
    } else if (id == 'data-menu-preloadlog') {
        articles.hide();
        preloadlog.show();
    }

    if (id == 'data-menu-articles' && SelectedGetItem(SUBLINE, 'id'))
        $ActivateInfoData(1);
    else
        $ActivateInfoData(0);

    selected_data_menu.addClass('selected');
    selected_data_menu_id = id;
}

function $HideLogPage() {
    if (current_subline) {
        var selected_item = SelectedGetItem(SUBLINE, 'ob');
        if (selected_item != null)
            $onToggleSelectedClass(SUBLINE, selected_item, 'remove', null);
    }
}
/*
function $ShowLogPage() {
    if (current_subline) {
        $onToggleSelectedClass(SUBLINE, current_subline, 'add', null);
    }
}
*/
function $ResetLogPage() {
    current_subline = null;
    $("#command").val('');
}

function $onPaginationFormSubmit(frm) {
    return true;
}

function $onFilterFormSubmit(frm) {
    return true;
}

function $onParentFormSubmit(id) {
    var frm = $("#"+id);
    var action = frm.attr('action');

    //alert(frm.attr('id'));

    frm.submit();
}

function $onToggleSelectedClass(key, ob, action, command) {
    var id = ob != null ? ob.attr('id') : SelectedGetItem(key, 'id');
    var mask = [LINE, SUBLINE].indexOf(key) > -1 ? 'td' : 'dd';

    //alert(id+':'+action);

    $("#command").val(command != null ? command : '');

    if (action == 'submit') {
        $("input[name^='preload_id']").each(function() { $(this).val(id); });
        $onParentFormSubmit('filter-form');
    } else {
        $(mask, ob).each(function() {
            if (action == 'add') {
                $(this).addClass("selected");
                if (key == LINE)
                    $("input[name^='preload_id']").each(function() { $(this).val(id); });
                SelectedSetItem(key, 'ob', ob);
            }
            else
                $(this).removeClass("selected");
        });
    }
}

// ===========================
// Dialog windows declarations
// ===========================

function MakeFilterSubmit() {
    $ResetLogPage();
    $setPaginationFormSubmit();
    $onParentFormSubmit('filter-form');
}

// ====================
// Page Event Listeners
// ====================

jQuery(function($) 
{
    // ----------------------
    // Select log row (click)
    // ----------------------
    function $onLogClick(ob) {
        if (isWebServiceExecute)
            return;

        SelectedSetItem(LINE, 'id', null);
        $GetLogItem(ob);
    } 

    $("#line-content").on('click', '.log-row', function(e) {
        SelectedSetItem(LINE, 'num', 0);
        $onLogClick($(this));
        e.preventDefault();
    });

    // ----------------------------
    // Select log page (Pagination)
    // ----------------------------

    function $onSubmitPage() {
        if (isWebServiceExecute)
            return;

        $_reset_page();

        if (current_page) {
            IsGoPagination = true;

            $Go();
        }
    }

    function $onSortClick(ob) {
        $_next_current_sort();

        var x = LOG_SORT[current_sort];
        ob.attr('title', page_sort_title+(x ? ' ['+x+']' : ''));

        $onSubmitPage();
    }

    $("#sort_icon").click(function(e) {
        $onSortClick($(this));
        e.preventDefault();
    });

    // -------------------
    // Page's Table & Form
    // -------------------

    $("#per-page").on('change', function(e) {
        $setPaginationFormSubmit();
    });

    $("a[class^='nav']").click(function(e) {
        var ob = $(this);
        if (ob.hasClass('disabled'))
            e.preventDefault();
    });    

    $(".line").click(function(e) {
        var ob = $(this);
        $onToggleSelectedClass(LINE, ob, 'submit', null);
    });

    $(".subline").click(function(e) {
        current_subline = $(this);

        $HideLogPage();
        SelectedSetItem(SUBLINE, 'ob', current_subline);

        //$Go('401');
    });

    // -------------------------
    // Bottom side Data infomenu
    // -------------------------

    $("div[id^='data-menu']", this).click(function(e) {
        var ob = $(this);
        var id = ob.attr('id');
        var action = 
            id == 'data-menu-preloadlog' ? '401' : null
            ;

        if (action != null)
            $Go(action);
        else
            $ShowMenu(id);
    });

    // -------------
    // Command Panel
    // -------------

    $("#refresh").click(function(e) {
        $("#command").val('refresh');
        $onParentFormSubmit('filter-form');
        e.preventDefault();
    });

    $("#init-filter").click(function(e) {
        $("#command").val('init-filter');
        $onParentFormSubmit('init-form');
        e.preventDefault();
    });

    $("#export").click(function(e) {
        $("#command").val('export');
        $onParentFormSubmit('filter-form');
        e.preventDefault();
    });

    // ---------------------
    // Search context events
    // ---------------------

    function $onSearchSubmit(e) {
        var s = strip($("#search-context").val());
        if (s.length>0) {
            search_context = s;
            $("input[id^='searched']").each(function() { $(this).val(s); });
            is_search_activated = true;

            $_reset_current_sort();
            $onSubmitPage();
        }
    }

    $("#search-context").focusin(function(e) {
        is_search_focused = true;
    }).focusout(function(e) {
        is_search_focused = false;
    });

    $("#search-icon").click(function(e) {
        $onSearchSubmit(null);
        $onParentFormSubmit('filter-form');
    });

    $("#search-form").submit(function(e) {
        $onSearchSubmit(e);
    });

    // -------------
    // Resize window
    // -------------

    // --------
    // Keyboard
    // --------
});

// =======
// STARTER
// =======

$(function() 
{
    if (IsTrace)
        alert('Document Ready (preload)');

    $("#search-context").attr('placeholder', 'Найти (имя файла, артикул)...');

    $_init();
});


