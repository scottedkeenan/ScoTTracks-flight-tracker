# Prevent traceback on assert fail
__unittest = True

import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from statistics import mean, median


class ScottracksHomeLoadTime(unittest.TestCase):

    def setUp(self):
        self.driver = webdriver.Chrome()
        # self.url = 'http://0.0.0.0'
        self.url = 'https://scottedkeenan.co.uk'
        self.page_loads = 10
        # Load the page once to get the browser running
        self.driver.get(self.url)

    def time_page_load(self, url, driver):
        start_time = time.time()
        driver.get(self.url)
        end_time = time.time()

        # Check page loaded by looking for logo
        self.assertTrue(driver.find_element(By.XPATH, '/html/body/div[1]/div/nav/div/img'))

        total_time = end_time - start_time
        print(f"Page Load Time: {total_time} seconds")
        return total_time

    def test_home_page_load(self):
        load_times = []
        for i in range(10):
            load_time = self.time_page_load(self.url, self.driver)
            load_times.append(load_time)

        mean_load_time = mean(load_times)
        median_load_time = median(load_times)

        print(f'Load times for {self.url}')
        print(f'Mean {mean_load_time}')
        print(f'Median {median_load_time}')

        with self.subTest():
            self.assertLessEqual(mean_load_time, 0.5)
        with self.subTest():
            self.assertLessEqual(median_load_time, 0.5)

    def tearDown(self):
        self.driver.quit()

if __name__ == "__main__":
    unittest.main()
