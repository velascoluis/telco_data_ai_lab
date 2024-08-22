#!/bin/sh
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#........................................................................
# Purpose: Application local test
#........................................................................

export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
python3 -m venv local_test_env
source local_test_env/bin/activate
pip3 install -r requirements.txt
streamlit run webapp.py --server.port=8081 --server.enableCORS=false --server.enableXsrfProtection=false
deactivate