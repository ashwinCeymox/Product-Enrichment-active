import axios from 'axios';
import FormData from 'form-data';
import fs from 'fs';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

const formData = new FormData();
formData.append('file', fs.createReadStream('test.csv'));

api.post('/jobs/upload-csv?task_name=task-1&url_column=url&priority=normal', formData)
  .then(res => console.log(res.status, res.data))
  .catch(err => {
    console.log(err.response?.status);
    console.log(JSON.stringify(err.response?.data, null, 2));
  });
