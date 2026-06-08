#!/bin/bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

models="ED BRAMS Ramspost"

for model in ${models}
do
   echo "========================================================================="
   echo " + Model ${model}: "
   echo "   "
   modellines=0
   model_src="${repo_root}/${model}/src"
   if [[ ! -d "${model_src}" ]]
   then
      echo "   - Missing source directory: ${model_src}"
      echo "========================================================================="
      echo "   "
      continue
   fi
   direcs=$(ls -1 "${model_src}")
   for dir in ${direcs}
   do
      case "${dir}" in
      test_cases|doc|preproc)
         echo "Skip" >> /dev/null
         ;;
      *)
         echo -n "   - Directory ${dir}: "
         files=$(/bin/ls -1 "${model_src}/${dir}"/*.F90 2> /dev/null)
         files="${files} $(/bin/ls -1 "${model_src}/${dir}"/*.f90 2> /dev/null)"
         files="${files} $(/bin/ls -1 "${model_src}/${dir}"/*.c 2> /dev/null)"
         dirlines=0
         for file in ${files}
         do
            nlines=$(sed "/^ *\$/ d" "${file}" | wc -l)
            let dirlines=${dirlines}+${nlines}
         done
         echo "${dirlines} lines"
         let modellines=${modellines}+${dirlines}
         ;;
      esac
   done
   echo "   - Total: ${modellines}"
   echo "========================================================================="
   echo "   "
   echo "   "
   echo "   "
done
