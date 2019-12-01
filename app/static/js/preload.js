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

function subline_refresh(filename) {
    $(".filename").each(function() { 
        $(this).html(filename);
    });
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

function $onPaginationFormSubmit(frm) {
    return true;
}

function $onFilterFormSubmit(frm) {
    return true;
}

function $onInfoContainerChanged() {
    //alert($_width('screen-min')-$("#sidebarFrame").width()+':'+$("#line-table").width());
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
        if (is_show_error)
            return;

        $LineSelector.onRefresh($(this));
    });

    $(".subline").click(function(e) {
        if (is_show_error)
            return;

        $SublineSelector.onRefresh($(this));
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




