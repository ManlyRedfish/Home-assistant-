Describe "Invoke-HAGet" {
    BeforeAll {
        # Dot source but provide dummy parameters to bypass the prompt from top-level param block
        . "$PSScriptRoot/export_ha_nuisance_evidence.ps1" -BaseUrl "dummy" -AccessToken "dummy" -StartDate (Get-Date) -EndDate (Get-Date) -OutputFolder "dummy"
    }

    It "returns Invoke-RestMethod results on success" {
        Mock Invoke-RestMethod {
            [pscustomobject]@{ ok = $true }
        }

        $result = Invoke-HAGet `
            -Uri "http://ha.local/api/states" `
            -Headers @{ Authorization = "Bearer secret-token" } `
            -Token "secret-token"

        $result.ok | Should -Be $true

        Assert-MockCalled Invoke-RestMethod -Times 1 -Exactly -ParameterFilter {
            $Uri -eq "http://ha.local/api/states" -and $Method -eq "Get"
        }
    }

    It "redacts the access token from thrown errors" {
        Mock Invoke-RestMethod {
            throw "Request failed with token secret-token"
        }

        {
            Invoke-HAGet `
                -Uri "http://ha.local/api/states" `
                -Headers @{ Authorization = "Bearer secret-token" } `
                -Token "secret-token"
        } | Should -Throw "*Home Assistant GET failed for 'http://ha.local/api/states'*"

        try {
            Invoke-HAGet `
                -Uri "http://ha.local/api/states" `
                -Headers @{ Authorization = "Bearer secret-token" } `
                -Token "secret-token"
        }
        catch {
            $_.Exception.Message | Should -Match "\[REDACTED_TOKEN\]"
            $_.Exception.Message | Should -Not -Match "secret-token"
        }
    }
}
