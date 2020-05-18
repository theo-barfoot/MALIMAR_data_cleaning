import ipywidgets as widgets
from IPython.display import display


def display_volume_slices(vol_collection):
    num_slices = max([len(volume) for volume in vol_collection.volumes.values()]) - 1
    widgets.interact(vol_collection.display_slices,
                     slice_idx=(widgets.IntSlider(min=0, max=num_slices, step=1, continuous_update=False)))


class RegistrationDashboard:
    def __init__(self, parent):
        self.registration = parent

        self.plot_output = widgets.Output()

        self.log = False
        self.log_check = widgets.Checkbox(description='log image', indent=False)
        self.log_check.observe(self.log_check_event, names='value')

        self.calc_btn = widgets.Button(description='Calculate')
        self.calc_btn.on_click(self.calc_btn_event)

        self.progress_bar = widgets.IntProgress()

        self.slider_grid = widgets.GridspecLayout(3, 2)
        self.fill_slider_grid()

        self.trans_btn = widgets.Button(description='Transform')
        self.trans_btn.on_click(self.transform_button_event)

        #todo: add check box for initiating smooth method

    def log_check_event(self, change):
        self.log = change.new

    def calc_btn_event(self, b):
        self.progress_bar.max = len(self.registration.volume)
        self.progress_bar.value = 0
        self.registration.calculate(log=self.log, external_bar=self.progress_bar)
        self.plot()

    def plot(self):
        self.plot_output.clear_output(wait=True)
        with self.plot_output:
            self.registration.plot()

    def transform_button_event(self, b):
        self.registration.transform()
        self.disable_inputs()

    def disable_inputs(self):
        self.calc_btn.disabled = True
        self.trans_btn.disabled = True
        self.log_check.disabled = True
        for i in range(3):
            for j in range(2):
                self.slider_grid[i, j].disabled = True

    def __call__(self, *args, **kwargs):
        display(widgets.HBox([self.log_check, self.calc_btn, self.progress_bar, self.trans_btn]))
        self.plot()
        display(self.slider_grid)
        display(self.plot_output)

    def update_smooth(self, *args, **kwargs):
        self.registration.smooth(**kwargs)
        self.plot()

    def fill_slider_grid(self):
        self.slider_grid[0, 0] = widgets.IntSlider(min=1, max=50, value=15, description="x Kernal width",
                                     continuous_update=False, layout=widgets.Layout(width='auto', height='auto'))
        self.slider_grid[0, 1] = widgets.IntSlider(min=1, max=50, value=15, description="y Kernal width",
                                     continuous_update=False, layout=widgets.Layout(width='auto', height='auto'))
        self.slider_grid[1, 0] = widgets.FloatSlider(min=90.0, max=100.0, value=98.0, description="x Step Thresh %",
                                      continuous_update=False, layout=widgets.Layout(width='auto', height='auto'))
        self.slider_grid[1, 1] = widgets.FloatSlider(min=90.0, max=100.0, value=98.0, description="y Step Thresh %",
                                      continuous_update=False, layout=widgets.Layout(width='auto', height='auto'))
        self.slider_grid[2, 0] = widgets.IntSlider(min=20, max=50, value=30, description="x Min Step Length",
                                       continuous_update=False, layout=widgets.Layout(width='auto', height='auto'))
        self.slider_grid[2, 1] = widgets.IntSlider(min=20, max=50, value=30, description="y Min Step Length",
                                       continuous_update=False, layout=widgets.Layout(width='auto', height='auto'))

        self.slider_grid[0, 0].observe(self.k_x_event, names='value')
        self.slider_grid[0, 1].observe(self.k_y_event, names='value')
        self.slider_grid[1, 0].observe(self.st_x_event, names='value')
        self.slider_grid[1, 1].observe(self.st_y_event, names='value')
        self.slider_grid[2, 0].observe(self.msl_x_event, names='value')
        self.slider_grid[2, 1].observe(self.msl_y_event, names='value')

    def k_x_event(self, change):
        self.update_smooth(k_x=change.new, k_y=self.slider_grid[0, 1].value,
                           st_x=self.slider_grid[1, 0].value, st_y=self.slider_grid[1, 1].value,
                           msl_x=self.slider_grid[2, 0].value, msl_y=self.slider_grid[2, 1].value)

    def k_y_event(self, change):
        self.update_smooth(k_x=self.slider_grid[0, 0].value, k_y=change.new,
                           st_x=self.slider_grid[1, 0].value, st_y=self.slider_grid[1, 1].value,
                           msl_x=self.slider_grid[2, 0].value, msl_y=self.slider_grid[2, 1].value)

    def st_x_event(self, change):
        self.update_smooth(k_x=self.slider_grid[0, 0].value, k_y=self.slider_grid[0, 1].value,
                           st_x=change.new, st_y=self.slider_grid[1, 1].value,
                           msl_x=self.slider_grid[2, 0].value, msl_y=self.slider_grid[2, 1].value)

    def st_y_event(self, change):
        self.update_smooth(k_x=self.slider_grid[0, 0].value, k_y=self.slider_grid[0, 1].value,
                           st_x=self.slider_grid[1, 0].value, st_y=change.new,
                           msl_x=self.slider_grid[2, 0].value, msl_y=self.slider_grid[2, 1].value)

    def msl_x_event(self, change):
        self.update_smooth(k_x=self.slider_grid[0, 0].value, k_y=self.slider_grid[0, 1].value,
                           st_x=self.slider_grid[1, 0].value, st_y=self.slider_grid[1, 1].value,
                           msl_x=change.new, msl_y=self.slider_grid[2, 1].value)

    def msl_y_event(self, change):
        self.update_smooth(k_x=self.slider_grid[0, 0].value, k_y=self.slider_grid[0, 1].value,
                           st_x=self.slider_grid[1, 0].value, st_y=self.slider_grid[1, 1].value,
                           msl_x=self.slider_grid[2, 0].value, msl_y=change.new)