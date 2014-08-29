$(function () {
    Highcharts.setOptions({
        global: {
            timezoneOffset: new Date().getTimezoneOffset()
        },
        credits: {
            enabled: false
        },
        exporting: {
            enabled: true,
            buttons: {
                contextButton: {
                    menuItems: [{
                        text: 'Print Chart',
                        onclick: function() {
                            this.print();
                        }
                    }, {
                        text: 'Export to PNG',
                        onclick: function() {
                            var sv = $(this)[0].renderTo.children[0].firstChild;
                            sv.toDataURL("image/png", {callback: function(data) {
                                window.open(data);
                            }});
                        },
                        separator: false
                    }]
                }
            }
        },
        plotOptions: {
            spline: {
                marker: {
                    enabled: false
                },
                states: {
                    hover: {
                        lineWidth: 2
                    }
                }
            },
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                slicedOffset: 15
            },
            areaspline: {
                stacking: 'normal',
                marker: {
                    enabled: false
                },
                states: {
                    hover: {
                        lineWidth: 2
                    }
                }
            }
        },
        noData: {
            style: {
                fontWeight: 'bold',
                fontSize: '15px',
                color: '#303030'
            }
        },
        xAxis: {
            type: 'datetime',
            dateTimeLabelFormats: {
                millisecond: '%H:%M:%S',
                second: '%H:%M:%S',
                minute: '%H:%M',
                hour: '%H:%M',
                day: '%e. %b',
                week: '%e. %b',
                month: '%b \'%y',
                year: '%Y'
            },
            title: {
                text: 'Time'
            }
        }
    });
});
