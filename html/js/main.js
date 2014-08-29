$(function () {
    stat = {
        'auth:delay_count': 0,
        'auth:delay_sum': 0,
        'auth:delay_max': 0,
        'auth:delay_min': 999,
        'auth:timeout_count': 0,
        'accounting:delay_count': 0,
        'accounting:delay_sum': 0,
        'accounting:delay_max': 0,
        'accounting:delay_min': 999,
        'accounting:timeout_count': 0,
        'reject:count': 0,
        'reject:908': 0,
        'reject:909': 0,
        'request_count': 0
    };

    ajax = null;
    timer = new _timer();
    lastUpdateTime = 0;
    getStatsInterval = 0;

    authDelayAvg = new Highcharts.Chart({
        chart: {
            type: 'spline',
            renderTo: 'authDelayAvgChart',
            zoomType: 'x'
        },
        title: {
            text: 'Auth Average Delay'
        },
        yAxis: {
            title: {
                text: 'Seconds'
            }
        },
        series: [{
            name: 'Delay',
            data: []
        }]
    });

    authTimeout = new Highcharts.Chart({
        chart: {
            type: 'spline',
            renderTo: 'authTimeoutChart',
            zoomType: 'x'
        },
        title: {
            text: 'Auth Timeouts'
        },
        yAxis: {
            title: {
                text: 'Count'
            }
        },
        series: [{
            name: 'Count',
            data: []
        }]
    });

    authDelayPeriod = new Highcharts.Chart({
        chart: {
            type: 'areaspline',
            renderTo: 'authDelayPeriodChart'
        },
        title: {
            text: 'Auth Delay Period'
        },
        tooltip: {
            shared: true
        },
        series: [{
            name: '&lt;100',
            data: []
        }, {
            name: '100-500',
            data: []
        }, {
            name: '500-2000',
            data: []
        }, {
            name: '&gt;2000',
            data: []
        }]
    });

    accountingDelayAvg = new Highcharts.Chart({
        chart: {
            type: 'spline',
            renderTo: 'accountingDelayAvgChart'
        },
        title: {
            text: 'Accounting Average Delay'
        },
        yAxis: {
            title: {
                text: 'Seconds'
            }
        },
        series: [{
            name: 'Delay',
            data: []
        }]
    });

    accountingTimeout = new Highcharts.Chart({
        chart: {
            type: 'spline',
            renderTo: 'accountingTimeoutChart',
            zoomType: 'x'
        },
        title: {
            text: 'Accounting Timeouts'
        },
        yAxis: {
            title: {
                text: 'Seconds'
            }
        },
        series: [{
            name: 'Delay',
            data: []
        }]
    });

    accountingDelayPeriod = new Highcharts.Chart({
        chart: {
            type: 'areaspline',
            renderTo: 'accountingDelayPeriodChart'
        },
        title: {
            text: 'Accounting Delay Period'
        },
        tooltip: {
            shared: true
        },
        series: [{
            name: '&lt;100',
            data: []
        }, {
            name: '100-500',
            data: []
        }, {
            name: '500-2000',
            data: []
        }, {
            name: '&gt;2000',
            data: []
        }]
    });

    rejectCodes = new Highcharts.Chart({
        chart: {
            renderTo: 'rejectCodesChart'
        },
        title: {
            text: 'Reject Codes'
        },
        series: [{
            name: '908',
            data: []
        }, {
            name: '909',
            data: []
        }]
    });

    authDelayAvgSeries = authDelayAvg.series[0];
    authTimeoutSeries = authTimeout.series[0];

    accountingDelayAvgSeries = accountingDelayAvg.series[0];
    accountingTimeoutSeries = accountingTimeout.series[0];

    authDelayPeriodSeries0 = authDelayPeriod.series[0];
    authDelayPeriodSeries100 = authDelayPeriod.series[1];
    authDelayPeriodSeries500 = authDelayPeriod.series[2];
    authDelayPeriodSeries2000 = authDelayPeriod.series[3];

    accountingDelayPeriodSeries0 = accountingDelayPeriod.series[0];
    accountingDelayPeriodSeries100 = accountingDelayPeriod.series[1];
    accountingDelayPeriodSeries500 = accountingDelayPeriod.series[2];
    accountingDelayPeriodSeries2000 = accountingDelayPeriod.series[3];

    rejectCodesSeries908 = rejectCodes.series[0];
    rejectCodesSeries909 = rejectCodes.series[1];

    $('#start').click(function() {
        interval = $('#interval input').val() * 1000;
        getStatsInterval = setInterval(getStats, interval);
    });

    $('#stop').click(function() {
        clearInterval(getStatsInterval);
        timer.stop();
    });

    function start_timer(start_time) {
        if (!timer.getStatus()) {
            now = new Date().getTime() / 1000;
            timer.start(1000, parseInt(now - start_time));
        }
    }

    function getStats() {
        ajax = $.ajax({
            url: '/json',
            type: 'POST',
            data: {
                time: lastUpdateTime
            },
            success: function(data, textStatus, jqXHR){
                if (data == false || !data['time']) return;
                start_timer(data['start_time']);

                shift = authTimeoutSeries.data.length > 20; // shift if the series is
                // longer than 20

                $.each(data, function(index, row){
                    data[index] = parseFloat(row);
                });

                time = data['time'] * 1000; // Epoch * 1000

                stat['auth:timeout_count'] += data['auth:timeout_count'];
                stat['auth:delay_count'] += data['auth:delay_count'];
                stat['auth:delay_sum'] += data['auth:delay_sum'];
                stat['auth:delay_max'] = Math.max(stat['auth:delay_max'], data['auth:delay_max']);
                stat['auth:delay_min'] = Math.min(stat['auth:delay_min'], data['auth:delay_min']);
                stat['auth:delay_avg'] = stat['auth:delay_sum'] / stat['auth:delay_count'];

                stat['accounting:timeout_count'] += data['accounting:timeout_count'];
                stat['accounting:delay_count'] += data['accounting:delay_count'];
                stat['accounting:delay_sum'] += data['accounting:delay_sum'];
                stat['accounting:delay_max'] = Math.max(stat['accounting:delay_max'], data['accounting:delay_max']);
                stat['accounting:delay_min'] = Math.min(stat['accounting:delay_min'], data['accounting:delay_min']);
                stat['accounting:delay_avg'] = stat['accounting:delay_sum'] / stat['accounting:delay_count'];

                stat['reject:count'] += data['reject:count'];
                stat['request_count'] += data['request_count'];

                $('#authTimeoutCount span').text(stat['auth:timeout_count']);
                $('#authDelayMax span').text(stat['auth:delay_max'].toFixed(3));
                $('#authDelayMin span').text(stat['auth:delay_min'].toFixed(3));
                $('#authDelayAvg span').text(stat['auth:delay_avg'].toFixed(3));

                $('#accountingTimeoutCount span').text(stat['accounting:timeout_count']);
                $('#accountingDelayMax span').text(stat['accounting:delay_max'].toFixed(3));
                $('#accountingDelayMin span').text(stat['accounting:delay_min'].toFixed(3));
                $('#accountingDelayAvg span').text(stat['accounting:delay_avg'].toFixed(3));

                $('#requestCount span').text(stat['request_count']);

                authDelayPeriodSeries0.addPoint([time, data['auth:delay_period:<100']], false, shift);
                authDelayPeriodSeries100.addPoint([time, data['auth:delay_period:100-500']], false, shift);
                authDelayPeriodSeries500.addPoint([time, data['auth:delay_period:500-2000']], false, shift);
                authDelayPeriodSeries2000.addPoint([time, data['auth:delay_period:>2000']], false, shift);

                accountingDelayPeriodSeries0.addPoint([time, data['accounting:delay_period:<100']], false, shift);
                accountingDelayPeriodSeries100.addPoint([time, data['accounting:delay_period:100-500']], false, shift);
                accountingDelayPeriodSeries500.addPoint([time, data['accounting:delay_period:500-2000']], false, shift);
                accountingDelayPeriodSeries2000.addPoint([time, data['accounting:delay_period:>2000']], false, shift);

                authDelayPeriod.redraw();
                accountingDelayPeriod.redraw();

                authTimeoutSeries.addPoint([time, data['auth:timeout_count']], true, shift);
                accountingTimeoutSeries.addPoint([time, data['accounting:timeout_count']], true, shift);

                authDelayAvgSeries.addPoint([time, data['auth:delay_sum'] / data['auth:delay_count'].toFixed(3)], true, shift);
                accountingDelayAvgSeries.addPoint([time, data['accounting:delay_sum'] / data['accounting:delay_count'].toFixed(3)], true, shift);

                rejectCodesSeries908.addPoint([time, data['reject:908']], true, shift);
                rejectCodesSeries909.addPoint([time, data['reject:909']], true, shift);

                lastUpdateTime = data['time'];
            },
            error: function(jqXHR, textStatus, errorThrown){
                console.log('error: ' + textStatus);
            }
        });

    }

});
