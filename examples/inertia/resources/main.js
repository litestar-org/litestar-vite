import { createInertiaApp } from "@inertiajs/vue3"
import { createApp, h } from "vue"
import Layout from "./Layout.vue"
createInertiaApp({
	resolve: (name) => {
		const pages = import.meta.glob("./pages/**/*.vue", {
			eager: true,
		})
		const page = pages[`./pages/${name}.vue`]
		page.default.layout = page.default.layout || Layout
		return page
	},
	setup({ el, App, props, plugin }) {
		createApp({ render: () => h(App, props) })
			.use(plugin)
			.mount(el)
	},
})
